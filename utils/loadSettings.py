import json
import argparse


class LoadFromFile(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        with open(values, 'r') as config_file:
            config_dict = json.load(config_file)
        setattr(namespace, self.dest, config_dict)
