#!/usr/bin/env python3

""" Convert Python 2 pickle file to Python 3 pickle file """

import sys
import os.path
import shutil
import pickle
import argparse


def convert(filepath):
    """ Convert Python 2 pickle file """

    if not os.path.exists(filepath):
        print(f"File not found: '{filepath}'")
        return

    filename = os.path.basename(filepath)
    if filename not in ['connect.key', 'ofx_config.cfg']:
        print(f"Unsupported pickle file: '{filename}'")
        return

    infile = filename + '_p2'
    outfile = filename + '_p3'

    shutil.copy(filepath, infile)
    fin = open(infile, 'rb')
    fout = open(outfile, 'wb')

    if filename == 'connect.key':
        convert_key(fin, fout)
    elif filename == 'ofx_config.cfg':
        convert_cfg(fin, fout)

    fin.close()
    fout.close()
    return


def convert_key(fin, fout):
    """ Convert connect.key pickle """

    table = pickle.load(fin, encoding='bytes')
    table.update({k:v.decode('utf-8') for (k,v) in table.items()})
    pickle.dump(table, fout)

    return


def convert_cfg(fin, fout):
    """ Convert ofx_config.cfg pickle """

    pwkey = pickle.load(fin, encoding='bytes')

    if len(pwkey):
        pickle.dump(pwkey, fout)
        pickle.dump(pickle.load(fin), fout)

        accts = pickle.load(fin, encoding='bytes')
        for item in accts:
            item[0] = item[0].decode('utf-8')
            item[2] = item[2].decode('utf-8')
        pickle.dump(accts, fout)
    else:
        pickle.dump('', fout)
        pickle.dump(pickle.load(fin), fout)
        pickle.dump(pickle.load(fin), fout)

    return


def main(argv):
    """ Main """

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('filepath', help='Python 2 pickle filename [connect.key, ofx_config.cfg]')
    args = parser.parse_args(argv)

    convert(args.filepath)
    return


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
