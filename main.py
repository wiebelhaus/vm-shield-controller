#!/usr/bin/python -u
import os
import subprocess

import libvirt
import lxc

# Globals
vm_name = 'virt-windows'
vm_shieled = False
vm_cpus = '4-7'
sys_cpus = '0-3'
all_cpus = '0-7'
null_fd = open(os.devnull,'w')

def main():
    print("--> vm_shield_controller started! <--")
    libvirt.virEventRegisterDefaultImpl()
    conn = libvirt.open('qemu:///system')
    domain = conn.lookupByName(vm_name)

    on_start(domain)

    cb_id = conn.domainEventRegisterAny(
                domain, 
                libvirt.VIR_DOMAIN_EVENT_ID_LIFECYCLE, 
                vm_lifecycle_event, 
                None
            )

    # Blocking loop triggered by VM state changes
    while True:
        libvirt.virEventRunDefaultImpl()


def on_start(dom):
    #On start check status of VM
    state, reason = dom.state()

    if state == libvirt.VIR_DOMAIN_RUNNING:
        print("on_start(): VM is running, shielding VM VCPUs")
        shield_vm()
    else:
        print("on_start(): VM is not running, attempting to unshield VCPUs")
        unshield_vm()

def vm_lifecycle_event(conn, domain, event, detail, opaque):
    if event == libvirt.VIR_DOMAIN_EVENT_STARTED:
        print("vm_lifecycle_event(): VM just started, call func to shield VCPUs")
        shield_vm()
    else:
        print("vm_lifecycle_event(): Some other event occured, probably suspend or sleep")
        unshield_vm()
        
def shield_vm():
    if cset_shield() == 0:
        print("shield_vm(): cset_shield was successful.")
    else:
        print("shield_vm(): cset_shield was unsuccessful.")

    lxc_cgroup_shield()
    return

def unshield_vm():
    if cset_unshield() == 0:
        print("unshield_vm(): cset_unshield was successful.")
    else:
        print("unshield_vm(): cset_unshield was unsuccessful.")

    lxc_cgroup_unshield()
    return

def cset_shield():
    rc = 0
    rc += subprocess.call("cset set -c " + all_cpus + " -s machine.slice", shell=True, stdout=null_fd)
    rc += subprocess.call("cset shield --kthread on --cpu " + vm_cpus, shell=True, stdout=null_fd)
    return rc

def cset_unshield():
    return subprocess.call("cset shield --reset", shell=True, stdout=null_fd)

def lxc_cgroup_shield():
    for container in lxc.list_containers(as_object=True):
        if container.running:
            print("lxc_cgroup_shield(): Restricting CPUs for " + container.name + " to " + sys_cpus)
            container.set_config_item("lxc.cgroup.cpuset.cpus", sys_cpus)

def lxc_cgroup_unshield():
    for container in lxc.list_containers(as_object=True):
        if container.running:
            print("lxc_cgroup_unshield(): Unrestricting CPUs for " + container.name + " to " + all_cpus)
            container.set_config_item("lxc.cgroup.cpuset.cpus", all_cpus)

# virDomainEventType is emitted during domain lifecycles (see libvirt.h)
VIR_DOMAIN_EVENT_MAPPING = {
    0: "VIR_DOMAIN_EVENT_DEFINED",
    1: "VIR_DOMAIN_EVENT_UNDEFINED",
    2: "VIR_DOMAIN_EVENT_STARTED",
    3: "VIR_DOMAIN_EVENT_SUSPENDED",
    4: "VIR_DOMAIN_EVENT_RESUMED",
    5: "VIR_DOMAIN_EVENT_STOPPED",
    6: "VIR_DOMAIN_EVENT_SHUTDOWN",
    7: "VIR_DOMAIN_EVENT_PMSUSPENDED",
}

VIR_DOMAIN_STATE_MAPPING = {
    0: "VIR_DOMAIN_NOSTATE",
    1: "VIR_DOMAIN_RUNNING",
    2: "VIR_DOMAIN_BLOCKED",
    3: "VIR_DOMAIN_PAUSED",
    4: "VIR_DOMAIN_SHUTDOWN",
    5: "VIR_DOMAIN_SHUTOFF",
    6: "VIR_DOMAIN_CRASHED",
    7: "VIR_DOMAIN_PMSUSPENDED",
}

if __name__ == "__main__":
    main()
