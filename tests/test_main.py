import pytest
from unittest.mock import patch, mock_open
from main import load_rules, send_to_webhook
import json

def test_load_rules():
    """
    Tests that the load_rules function correctly loads rules from a CSV file.
    """
    csv_data = '''"match","handling","team"
"error","Ticket and Page","NOC"'''
    with patch('builtins.open', mock_open(read_data=csv_data)):
        rules = load_rules('dummy_path.csv')
        assert len(rules) == 1
        assert rules[0]['match'] == 'error'
        assert rules[0]['handling'] == 'Ticket and Page'
        assert rules[0]['team'] == 'NOC'

@patch('subprocess.run')
def test_send_to_webhook(mock_subprocess_run):
    """
    Tests that the send_to_webhook function calls curl with the correct arguments.
    """
    message = {'message': 'This is a test message', 'handling': 'Ticket', 'team': 'DevOps'}
    send_to_webhook(message)
    message_json = json.dumps(message)
    expected_command = [
        "curl",
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", message_json,
        "https://your-webhook-url.com"
    ]
    mock_subprocess_run.assert_called_once_with(expected_command, check=True)
