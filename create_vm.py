#!/usr/bin/env python3

from ironsight_harvester_api import create_vm, list_templates
import sys

if __name__ == "__main__":

    if "--templates" in sys.argv:
        list_templates()
        sys.exit(0)

    if len(sys.argv) < 4:
        print("Usage: python3 create_vm.py [vmName] [template] [studentName] [template_override]")
        sys.exit(1)
    vmName = str(sys.argv[1])
    template_choice = str(sys.argv[2])
    userName = str(sys.argv[3])
    if len(sys.argv) > 4:
        template_override = str(sys.argv[4])
    else:
        template_override = None
    # Create virtual machine
    create_vm(vmName, template_choice, userName, template_override)