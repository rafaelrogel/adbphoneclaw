#!/usr/bin/env python3
# bt_agent.py — BlueZ agent NoInputNoOutput (auto-confirma pareamento).
# systemd: /etc/systemd/system/bt-agent.service
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

AGENT_PATH = "/org/bluez/agent"
BUS_NAME = "org.bluez"
SERVICE = "org.bluez"
AGENT_IFACE = "org.bluez.Agent1"


class Agent(dbus.service.Object):
    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Release(self):
        print("Release")

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        return "0000"

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        print(f"DisplayPinCode {pincode}")

    @dbus.service.method(AGENT_IFACE, in_signature="ouq", out_signature="")
    def RequestConfirmation(self, device, passkey):
        # auto-confirma qualquer pareamento
        return

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        return dbus.UInt32(0)

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def Authorize(self, device, uuid):
        return

    @dbus.service.method(AGENT_IFACE, in_signature="ou", out_signature="")
    def AuthorizeService(self, device, uuid):
        return

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="")
    def Cancel(self):
        print("Cancel")


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    bus.request_name(BUS_NAME)
    agent = Agent(bus, AGENT_PATH)
    manager = dbus.Interface(
        bus.get_object(BUS_NAME, "/org/bluez"), "org.bluez.AgentManager1"
    )
    manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")
    manager.RequestDefaultAgent(AGENT_PATH)
    print("bt-agent registered (NoInputNoOutput)")
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
