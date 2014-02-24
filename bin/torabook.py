#!/usr/bin/env python2.7

import urllib2
import re
import jinja2
import sys, os

CHECK_IP=sys.argv[1]
TMPDIR=(sys.argv[2:3] or ['.'])[0]     # neato.

GROUP_NAME = 'TOR_ABOOK'
ZONE_NAME = 'untrust'

AB_SET_SZ = 1000
AB_SET_NAME = 'TOR-Exit-Servers'

# the URL to retreive the ip list information
URL = 'https://check.torproject.org/cgi-bin/TorBulkExitList.py?ip='+CHECK_IP

SAVE_FILE = open(os.path.join(TMPDIR,'TOR_abook.set'), 'w+')

TOP_EDIT = """
top
delete groups {group}
edit groups {group}
edit security zones security-zone {zone} address-book
""".format(group=GROUP_NAME, zone=ZONE_NAME)

SAVE_FILE.write( TOP_EDIT )

### ---------------------------------------------------------------------------
### retrieve the list of IP addresses from the website
### ---------------------------------------------------------------------------

sd = re.compile('\d')

print "fetching data from URL: "+URL
ipaddr_list = filter(lambda x: sd.match(x), urllib2.urlopen(URL).read().split('\n'))
ipaddr_list = list(set(ipaddr_list))  # cheap way of removing duplicates ...

c_ipaddr_list = len(ipaddr_list)
print "fetched {} addresses".format(c_ipaddr_list)

### ---------------------------------------------------------------------------
### create the address items for each ip-address
### ---------------------------------------------------------------------------

def create_address_items():
  t_ab_items = """
  {%- for ipaddr in ipaddr_list %}
set address {{ ipaddr }}/32 {{ ipaddr }}/32
  {%- endfor %}
  """

  # render the data through the template to produce the result of commands
  setcmds = jinja2.Template(t_ab_items).render( 
    zone=ZONE_NAME, ipaddr_list=ipaddr_list )

  SAVE_FILE.write(setcmds)

create_address_items()

### ---------------------------------------------------------------------------
### Now create address-set items for each <AB_SET_SZ> items
### ---------------------------------------------------------------------------

def create_address_set_blocks():
  c_ab_sets = int(round((c_ipaddr_list) / float(AB_SET_SZ)))
  print "creating {} address-book sets ...".format(c_ab_sets)

  t_ab_set = """
  {%- for ipaddr in ipaddr_list %}
set address-set {{ ab_set_name }} address {{ ipaddr }}/32
  {%- endfor %}
  """
  jt_ab_set = jinja2.Template(t_ab_set)

  for ab_set_idx in range(c_ab_sets):
    start = ab_set_idx * AB_SET_SZ
    end = start + AB_SET_SZ - 1
    ipaddr_slice = ipaddr_list[start:end]
    ab_set_name = "{}{}".format(AB_SET_NAME, ab_set_idx)
    setcmds = jt_ab_set.render(zone=ZONE_NAME, ab_set_name=ab_set_name, ipaddr_list=ipaddr_slice)
    SAVE_FILE.write(setcmds)

create_address_set_blocks()

### ---------------------------------------------------------------------------
### Now create a toplevel address book set that includes each of the 'chunks'
### ---------------------------------------------------------------------------

def create_address_set_top():
  t_ab_set = """
  {%- for idx in range(c_sets) %}
set address-set {{ ab_set_name }} address-set {{ ab_set_name }}{{ idx }}
  {%- endfor %}
  """

  print "creating address book {} ...".format( AB_SET_NAME)
  setcmds = jinja2.Template(t_ab_set).render(zone=ZONE_NAME, ab_set_name=AB_SET_NAME, c_sets=c_ab_sets)
  SAVE_FILE.write(setcmds)

LAST = """
top
set apply-groups {group}
""".format(group=GROUP_NAME)

SAVE_FILE.write(LAST)
SAVE_FILE.close()