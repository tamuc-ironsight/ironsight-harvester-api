#!/usr/bin/env python3

from ironsight_harvester_api import handle_event
import sys
from pprint import pprint

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 event_handler.py [endoded_data]")
        print("\nExample pre-encoded data:")
        # Pre-endoded data example:
        example = {
            "action": "create",
            "type": "user",
            "data": {
                "first_name": "John",
                "last_name": "Doe",
                "user_name": "john_doe",
                "password": "password",
                "roles": [
                    "user"
                ],
                "courses": [
                    "csci_440",
                    "csci_359"
                ],
                "profile_pic_data": "",
                "tags": [
                    "linux"
                ]
            }
        }
        pprint(example)
        sys.exit(1)
    encoded_data = str(sys.argv[1])
    handle_event(encoded_data)
