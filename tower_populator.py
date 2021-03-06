#! /usr/bin/env python

import yaml
import sys
import tower_cli
import time
from select import select
import os.path
from getpass import getpass

class Config:
    def __init__(self, **entries):
        self.__dict__.update(entries)

# load configuration
c = yaml.load(open(sys.argv[1]).read())
tower = Config(**c)

user_res = tower_cli.get_resource('user')
team_res = tower_cli.get_resource('team')
org_res = tower_cli.get_resource('organization')
cred_res = tower_cli.get_resource('credential')
inv_res = tower_cli.get_resource('inventory')
host_res = tower_cli.get_resource('host')
group_res = tower_cli.get_resource('group')
project_res = tower_cli.get_resource('project')
job_template_res = tower_cli.get_resource('job_template')

print "\nCreating Organization\n"
print tower.org, tower.org_desc
# create organization
org = org_res.create(name=tower.org, description=tower.org_desc)
org_id = org['id']

if tower.users:
    print "\nCreating Users\n"
    # create users
    for u in tower.users:
        print u
        user = user_res.create(**u)
        org_res.associate(org_id, user['id'])

if tower.teams:
    print "\nCreating Teams\n"
    # create teams
    for t in tower.teams:
        print t
        t['organization'] = org_id
        team = team_res.create(**t)
        for u in t['users']:
            user = user_res.get(username=u)
            team_res.associate(team['id'], user['id'])

if tower.credentials:
    print "\nCreating Credentials\n"
    # create credentials
    for c in tower.credentials:
        print c
        if c.has_key('team') and c.has_key('user'):
            print "Creds must have either team or user, not both."
            sys.exit(1)
        if c.has_key('team'):
            team = team_res.get(name=team['name'])
            c['team'] = team['id']
        if c.has_key('user'):
            user = user_res.get(name=user['name'])
            c['user'] = user['id']
        if c.has_key('private_key'):
            key_file_path = os.path.expanduser(c['private_key'])
            c['ssh_key_data'] = open(key_file_path, 'r')
        if c.has_key('private_key_password'):
            if c['private_key_password'] == 'prompt':
                c['ssh_key_unlock'] = getpass('Enter your ssh key password: ')
            else:
                c['ssh_key_unlock'] = c['private_key_password']
        c = cred_res.create(**c)

if tower.inventories:
    # create inventories
    print "\nCreating Inventories\n"
    for i in tower.inventories:
        print i
        i['organization'] = org_id
        inv = inv_res.create(**i)
        # create dynamic groups, static ones can be imported better with awx-manage
        if i.has_key('groups'):
            for g in i['groups']:
                print g
                g['inventory'] = inv['id']
                # set the credential if this group has one
                if g.has_key('credential'):
                    cred = cred_res.get(name=g['credential'])
                    g['credential'] = cred['id']
                group = group_res.create(**g)
                # sync the group if it has a credential
                if group.has_key('group'):
                    id = group['group']
                elif group.has_key('id'):
                    id = group['id']
                if g.has_key('credential'):
                    group_res.sync(id)
                if g.has_key('hosts'):
                    for h in g['hosts']:
                        h['inventory'] = inv['id']
                        print h
                        host = host_res.create(**h)
                        host_res.associate(host['id'], group['id'])

if tower.projects:
    # create projects
    print "\nCreating Projects\n"
    for p in tower.projects:
        print p
        p['organization'] = org_id
        project_res.create(**p)

if tower.job_templates:
    print "Waiting 60 seconds for projects to index."
    print "Press any key to skip if you know what you're doing."
    timeout = 60
    rlist, wlist, xlist = select([sys.stdin], [], [], timeout)
    # create job templates
    print "\nCreating Job Templates\n"
    for j in tower.job_templates:
        print j
        cred = cred_res.get(name=j['machine_credential'])
        j['credential'] = cred['id']
        inv = inv_res.get(name=j['inventory'])
        j['inventory'] = inv['id']
        project = project_res.get(name=j['project'])
        j['project'] = project['id']
        j['organization'] = org_id
        job_template_res.create(**j)
