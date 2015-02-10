#!/usr/bin/env python3

import datetime
import json

def print_json(text):
	print(">>>>>>",
	      str(datetime.datetime.now()),
	      "\n",
	      json.dumps(text, indent=2))

HOOKS = {
	"tweet": print_json
}