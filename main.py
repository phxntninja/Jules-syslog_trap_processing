import socketserver
import csv
import json
import subprocess
import asyncio
import os
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp.carrier.asyncio.dgram import udp

def send_to_webhook(message):
    """
    Formats a curl command and sends the message to a webhook.
    """
    webhook_url = os.environ.get("WEBHOOK_URL", "https://your-webhook-url.com")
    message_json = json.dumps(message)
    curl_command = [
        "curl",
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", message_json,
        webhook_url
    ]
    try:
        subprocess.run(curl_command, check=True)
        print("Successfully sent to webhook.")
    except subprocess.CalledProcessError as e:
        print(f"Error sending to webhook: {e}")

def load_rules(filename="data/rules.csv"):
    """
    Loads rules from a CSV file.
    """
    rules = []
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rules.append(row)
    return rules

class MyTCPServer(socketserver.ThreadingTCPServer):
    def __init__(self, server_address, RequestHandlerClass, rules):
        super().__init__(server_address, RequestHandlerClass)
        self.rules = rules

class SyslogHandler(socketserver.StreamRequestHandler):
    """
    This handler will be called for each incoming syslog message.
    """
    def handle(self):
        data = self.rfile.readline().strip()
        try:
            message = json.loads(data.decode('utf-8'))
        except json.JSONDecodeError:
            print(f"Could not decode message: {data}")
            return

        for rule in self.server.rules:
            if rule['match'] in message.get('message', ''):
                print(f"Matched rule: {rule['match']}")
                message['handling'] = rule['handling']
                message['team'] = rule['team']
                send_to_webhook(message)
                break
        print(f"Processed message: {message}")

# Callback function for receiving traps
async def snmp_trap_callback(snmpEngine, stateReference, contextEngineId, contextName, varBinds, cbCtx):
    print("Received SNMP trap:")
    trap_message = {}
    for name, val in varBinds:
        trap_message[name.prettyPrint()] = val.prettyPrint()
        print('%s = %s' % (name.prettyPrint(), val.prettyPrint()))

    rules = cbCtx['rules']
    for rule in rules:
        for name, val in varBinds:
            if rule['match'] in name.prettyPrint() or rule['match'] in val.prettyPrint():
                print(f"Matched rule: {rule['match']}")
                trap_message['handling'] = rule['handling']
            trap_message['team'] = rule['team']
            send_to_webhook(trap_message)
            break

async def start_snmp_listener(rules):
    snmpEngine = engine.SnmpEngine()
    # Transport setup
    config.addTransport(
        snmpEngine,
        udp.domainName,
        udp.UdpTransport().openServerMode(('0.0.0.0', 8162))
    )

    # SNMPv1/2c setup
    config.addV1System(snmpEngine, 'my-area', 'public')

    print("Starting SNMP trap listener on port 8162...")
    ntfrcv.NotificationReceiver(snmpEngine, snmp_trap_callback, None, {'rules': rules})

    await asyncio.get_running_loop().create_future()

def main():
    """
    Main function to start the syslog and SNMP trap listeners.
    """
    rules = load_rules()

    loop = asyncio.get_event_loop()

    # Start syslog listener in a separate thread
    syslog_server = MyTCPServer(("0.0.0.0", 8154), SyslogHandler, rules)
    syslog_thread = asyncio.to_thread(syslog_server.serve_forever)


    async def run_listeners():
        await asyncio.gather(
            start_snmp_listener(rules),
            syslog_thread
        )

    try:
        loop.run_until_complete(run_listeners())
    except KeyboardInterrupt:
        pass
    finally:
        syslog_server.shutdown()
        loop.close()

if __name__ == "__main__":
    main()
