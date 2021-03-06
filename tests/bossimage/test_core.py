import os

import yaml
from nose.tools import assert_equal, assert_raises
from voluptuous import MultipleInvalid, TypeInvalid

import bossimage.cli as cli
import bossimage.core as bc

def test_merge_config():
    expected = {
        'amz-2015092-default': {
            'ami_name': '%(role)s-%(profile)s-%(version)s-%(platform)s',
            'associate_public_ip_address': True,
            'become': True,
            'block_device_mappings': [{
                'device_name': '/dev/sdf',
                'ebs': {
                    'delete_on_termination': True,
                    'volume_size': 100,
                    'volume_type': 'gp2'
                }
            }],
            'connection': 'ssh',
            'connection_timeout': 600,
            'extra_vars': {},
            'instance_type': 't2.micro',
            'platform': 'amz-2015092',
            'port': 22,
            'profile': 'default',
            'security_groups': [],
            'source_ami': 'amzn-ami-hvm-2015.09.2.x86_64-gp2',
            'subnet': '',
            'username': 'ec2-user',
            'user_data': '',
            'tags': {
                'Name': 'hello',
                'Description': 'A description',
            },
         },
        'win-2012r2-default': {
            'ami_name': 'ami-00000000',
            'associate_public_ip_address': True,
            'become': False,
            'block_device_mappings': [],
            'connection': 'winrm',
            'connection_timeout': 300,
            'extra_vars': {},
            'instance_type': 'm3.medium',
            'platform': 'win-2012r2',
            'port': 5985,
            'profile': 'default',
            'security_groups': [],
            'source_ami': 'Windows_Server-2012-R2_RTM-English-64Bit-Base-2016.02.10',
            'subnet': '',
            'username': 'Administrator',
            'user_data': '',
            'tags': {},
       }
    }

    c = bc.load_config('tests/resources/boss-good.yml')

    assert_equal(c, expected)

def test_userdata():
    c = bc.load_config('tests/resources/boss-userdata.yml')

    win_2012r2 = c['win-2012r2-default']
    win_2012r2_user_data = '''<powershell>
winrm qc -q
winrm set winrm/config \'@{MaxTimeoutms="1800000"}\'
winrm set winrm/config/service \'@{AllowUnencrypted="true"}\'
winrm set winrm/config/service/auth \'@{Basic="true"}\'
Set-Item wsman:localhost\\client\\trustedhosts -value * -force
Get-NetFirewallProfile | Set-NetFirewallProfile -Enabled False\n</powershell>
'''
    assert_equal(bc.user_data(win_2012r2), win_2012r2_user_data)

    amz_2015092 = c['amz-2015092-default']
    amz_2015092_user_data = '''#!/bin/sh
pip install ansible
'''
    assert_equal(bc.user_data(amz_2015092), amz_2015092_user_data)

    centos_6 = c['centos-6-default']
    centos_6_user_data = '''#cloud-config
system_info:
  default_user:
    name: ec2-user
'''
    assert_equal(bc.user_data(centos_6), centos_6_user_data)

    centos_7 = c['centos-7-default']
    assert_equal(bc.user_data(centos_7), '')

def test_load_config_not_found():
    nosuchfile = bc.random_string(100)

    with assert_raises(bc.ConfigurationError) as r:
        bc.load_config(nosuchfile)

    assert_equal(
        r.exception.message,
        'Error loading {}: not found'.format(nosuchfile)
    )

def test_load_config_syntax_error():
    filename = 'tests/resources/boss-badsyntax.yml'

    with assert_raises(bc.ConfigurationError) as r:
        bc.load_config(filename)

    expected = "Error loading {}: expected token 'end of print statement', got ':', line 4"
    assert_equal(
        r.exception.message,
        expected.format(filename)
    )

def test_load_config_validation_error1():
    filename = 'tests/resources/boss-bad1.yml'

    with assert_raises(bc.ConfigurationError) as r:
        bc.load_config(filename)

    expected = "Error validating {}: required key not provided @ data['platforms'][0]['name']"
    assert_equal(
        r.exception.message,
        expected.format(filename)
    )

def test_load_config_validation_error2():
    filename = 'tests/resources/boss-bad2.yml'

    with assert_raises(bc.ConfigurationError) as r:
        bc.load_config(filename)

    expected = "Error validating {}: expected bool for dictionary value @ data['win-2012r2-default']['become']"
    assert_equal(
        r.exception.message,
        expected.format(filename)
    )

def test_env_vars():
    default_user = 'ec2-user'
    override_user = 'shisaboy'

    if 'BI_USERNAME' in os.environ: del(os.environ['BI_USERNAME'])

    c1 = bc.load_config('tests/resources/boss-env.yml')
    assert_equal(c1['amz-2015092-default']['username'], default_user)

    os.environ['BI_USERNAME'] = override_user
    c2 = bc.load_config('tests/resources/boss-env.yml')
    assert_equal(c2['amz-2015092-default']['username'], override_user)
