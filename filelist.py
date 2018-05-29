#!usr/bin/python

import os, sys
import hashlib
import re
import subprocess
import argparse
import datetime

''' A helper function that returns True if given argument is in a valid
YYYYMMDD orYYYYMMDDHHMMSS format. Raises error if not.
'''

def is_date(arg):
    # match is the MatchObject returned by the following search operation
    match = re.search(r'^([0-9]{4})([0-9]{2})([0-9]{2})(?:([0-9]{2})([0-9]{2})([0-9]{2})|)$', arg)
    # if there is a match
    if match:
        # group(1) is year, group(2) is month, group(3) is day
        month = int(match.group(2))
        day = int(match.group(3))
        # if the specified date is valid
        if int(month) <= 12 and not int(month) == 0 and int(day) <= 31 and not int(day) == 0:
            # if arg is in the form YYYYMMDDHHMMSS
            if match.group(4):
                # then group(4) is hour, group(5) is minute, group(6) is second
                hour = int(match.group(4))
                minute = int(match.group(5))
                second = int(match.group(6))
                # if specified time is valid
                if hour < 24 and minute < 60 and second < 60:
                    return arg
            # if arg is in the form YYYYMMDD
            else:
                return arg
    # raise an error if anything else
    raise argparse.ArgumentTypeError('Argument given is not a valid date/datetime')


'''
A helper function that returns True if given argument is in a valid
size format(e.g. 65k, 92M, 821). Raises error if not.
'''


def is_size(arg):
    # turn arg to lower case
    arg.lower()
    # match is the MatchObject returned by the following search operation
    match = re.search(r'^[0-9]+(?:k|m|t|g|)$', arg)
    # if there is a match
    if match:
        return arg
    # if no match
    else:
        # raise an error
        raise argparse.ArgumentTypeError('Argument given is not a valid size')


'''
A helper function that returns byte size value of the size expressions.
(e.g. returns 1024 if arg='1k')
'''


def argtosize(arg):
    # if arg is already in bytes
    if arg[-1:] in '0123456789':
        pass
    # if arg is in kilobytes
    elif arg[-1:] == 'k':
        arg = int(arg[:-1]) * 1024
    # if arg is in megabytes
    elif arg[-1:] == 'm':
        arg = int(arg)[:-1] * 1024 * 1024
    # if arg is in gigabytes
    elif arg[-1:] == 'g':
        arg = int(arg)[:-1] * 1024 * 1024 * 1024
    # if arg is in terabytes
    elif arg[-1:] == 't':
        arg = int(arg)[:-1] * 1024 * 1024 * 1024 * 1024

    return int(arg)


'''
Returns True if modification time of the current item is earlier than the
datetime argument given to the '-before' option. Returns False otherwise.
'''


def before(currentitem):
    # get modification time of the current item
    modtime = os.path.getmtime(currentitem)
    # rearrange the modification time to YYYYMMDDHHMMSS format
    modtime = datetime.datetime.fromtimestamp(modtime).strftime('%Y%m%d%H%M%S')
    given_arg = args.before[0]
    # if given arg is in YYYYMMDD format
    if len(given_arg) == 8:
        # then add 000000 at the end of it
        given_arg = int(given_arg) * 10 ** 6

    return int(modtime) < given_arg


'''
Returns True if modification time of the current item is later than the
datetime argument given to the '-after' option. Returns False otherwise.
'''


def after(currentitem):
    # get modification time of the currentitem
    modtime = os.path.getmtime(currentitem)
    # rearrange the modification time to YYYYMMDDHHMMSS format
    modtime = datetime.datetime.fromtimestamp(modtime).strftime('%Y%m%d%H%M%S')
    given_arg = args.after[0]
    # if given arg is in YYYYMMDD format
    if len(given_arg) == 8:
        # then add 000000 at the end of it
        given_arg = int(given_arg) * 10 ** 6

    return int(modtime) > given_arg


'''
Returns True if the file name of the currentitem(currentitem is a pathname) matches
the regular expression given as an argument to the "-match" option. Returns False otherwise.
'''


def match(currentitem):
    # capture the name of the path currentitem by the following search operation
    name = re.search(r'^(?:.*/|/.*/)(.+)$', currentitem).group(1)
    try:
        # return True if the name matches the regular expression given as argument
        return re.fullmatch(args.match[0], name)
    except:
        print("Invalid regex argument. Program will be terminated.")
        sys.exit(1)

'''
Returns True if the size of the currentitem is smaller than the size given as an
argument to the "-smaller" option. Returns False otherwise.
'''


def smaller(currentitem):
    # get size of the currentitem
    size = os.path.getsize(currentitem)
    given_arg = args.smaller[0]
    # turn arg to bytes
    given_arg = argtosize(given_arg)

    return size < given_arg


'''
Returns True if the size of the currentitem is bigger than the size given as an
argument to the "-bigger" option. Returns False otherwise.
'''


def bigger(currentitem):
    # get size of the currentitem
    size = os.path.getsize(currentitem)
    given_arg = args.bigger[0]
    # turn arg to bytes
    given_arg = argtosize(given_arg)

    return size > given_arg

'''
hashes the given file and using this hash as a key, appends the file name
to the value of this key in dupl_dict
'''
def duplcont_helper(currentitem):
    # create sha256 hash object to hash currentitem
    sha256 = hashlib.sha256()
    # define buffer size to read and hash file in chunks
    buf_size = 65536  # reading in 64kb chunks
    with open(currentitem, 'rb') as file:
        # read the file in BUF_SIZE chunks and send it to sha256 object
        while True:
            data = file.read(buf_size)
            # when there is no data left to read break the loop
            if not data:
                break
            # update method concatenates all the data given to it
            sha256.update(data)
    # now we can hash the data of currentitem
    hash = sha256.hexdigest()
    # update the value of hash by appending currentitem
    if dupl_dict.get(hash):
        dupl_dict[hash].append(currentitem)
    # add hash and a list containing currentitem as a key-value pair
    else:
        dupl_dict[hash] = [currentitem]
        # if -stats option is given increment the value of 'size_of_unique' in 
        # statistics dictionary by the given file's size
        if args.stats:
            statistics['size_of_unique'] += os.stat(currentitem).st_size
    return True

'''
appends the file to the value of the key in dupl_dict which is the given file's name
'''
def duplname_helper(currentitem):
    # extract filename from given path
    name = re.search(r'^(?:.*/|/.*/)(.+)$', currentitem).group(1)
    # update the value of name by appending currentitem
    if dupl_dict.get(name):
        dupl_dict[name].append(currentitem)
    # add name and a list containing currentitem as a key-value pair
    else:
        dupl_dict[name] = [currentitem]
    return True

'''
helper function for -stats option. increments the value of the key called
'size_of_listed' by the size of the given file
'''
def stats_helper(currentitem):
    # get the size of the given file and update the total size of listed files
    statistics['size_of_listed'] += os.stat(currentitem).st_size
    return True

'''
prints traversal statistics
'''
def stats():
    print("Total number of files visited:".ljust(40), str(statistics['files_visited']))
    print("Total size of files visited:".ljust(40), str(statistics['size_of_visited']))
    print("Total number of files listed:".ljust(40), end=" ")
    # if filelist is not empty, this means that -duplname or -duplcont are not given
    # in this case total number of files is simply the length of the list filelist
    if filelist:
        print(str(len(filelist)))
    # else file names are stored in dupl_dict, therefore we should print the sum
    # of lengths of all the values in dupl_dict
    else:
        print(str(sum(len(list) for list in dupl_dict.values())))
    print("Total size of files listed:".ljust(40), str(statistics['size_of_listed']))
    if args.duplcont:
        print("Total number of unique files listed:".ljust(40), str(len(dupl_dict)))
        print("Total size of unique files:".ljust(40), str(statistics['size_of_unique']))
    elif args.duplname:
        print("Total number of files with unique names:".ljust(40), str(len(dupl_dict)))

'''
deletes the file having the given path, notice that returning true or false does not matter
for this function, as it is called at the end of the traverse_funcs loop 
'''
def delete(currentitem):
    os.remove(currentitem)
    return True

'''
Zips the files in filelist or files in dupl_dict depending on the options
'''
def zip():
    #create a temporary directory to copy files 
    subprocess.check_output("mkdir tmp" , shell=True)
    #copy files into it
    if args.duplname or args.duplcont:
        for files in dupl_dict.values():
            for file in files:
                subprocess.check_output('cp --backup=numbered "' + file + '" tmp',shell=True)
    else:
        for file in filelist:
            subprocess.check_output('cp --backup=numbered "' + file + '" tmp',shell=True)
    try:
        # zip the tmp directory with the given zip file name
        subprocess.check_output("zip " + args.zip[0] + " -rj tmp", shell=True)
    except subprocess.CalledProcessError:
          print("Files could not be zipped.")
    # after zipping we can delete the tmp directory
    subprocess.check_output("rm -r tmp", shell=True)

'''
This function appends the given item to the list called filelist and returns true
'''
def append_to_filelist(currentitem):
    filelist.append(currentitem)
    return True
    

parser = argparse.ArgumentParser(prog='filelist')
parser.add_argument('-before', nargs=1, type=is_date)
parser.add_argument('-after', nargs=1, type=is_date)
parser.add_argument('-match', nargs=1)
parser.add_argument('-smaller', nargs=1, type=is_size)
parser.add_argument('-bigger', nargs=1, type=is_size)
group1 = parser.add_mutually_exclusive_group()
group1.add_argument('-delete', action='store_true')
group1.add_argument('-zip', nargs=1)
group2 = parser.add_mutually_exclusive_group()
group2.add_argument('-duplcont', action='store_true')
group2.add_argument('-duplname', action='store_true')
parser.add_argument('-stats', action='store_true')
parser.add_argument('-nofilelist', action='store_true')
parser.add_argument('directory', action='append', nargs='*')

args = parser.parse_args()

traverse_fncs = [[before, args.before], [after, args.after], [match, args.match], [smaller, args.smaller],
                 [bigger, args.bigger],
                 [duplcont_helper, args.duplcont], [duplname_helper, args.duplname], [stats_helper, args.stats],
                 [delete, args.delete]]

# dictionary to store required statistics for the -stats option
statistics = {'files_visited': 0, 'size_of_visited': 0, 'size_of_listed': 0, 'size_of_unique': 0}

stack = list(reversed(args.directory[0]))
if not stack:
    stack = ['.']

# dictionary to store file names if one of -duplcont or -duplname is given.
# In the case of -duplcont hashes of the files are keys and files with the
# same hash are stored in lists as values. In the case of -duplname file names
# are the keys and the files having the same names are stored in lists as values.
dupl_dict = {}
# if none of -duplcont and -duplname is used, this list stores the files that satisfy the given options
filelist = []
# when neither -duplname nor -duplcont is used, as we should add the files to filelist, we define an anonymous
# function to achieve that. To make it called when traverse_fncs list is traversed, we change traverse_fncs[5][0]
# which corresponds to duplcont_helper function, to this anonymous function. That way instead of calling
# duplcont_helper, files are added to filelist.
if not args.duplname and not args.duplcont:
    traverse_fncs[5][0] = append_to_filelist
    traverse_fncs[5][1] = True

# below traversal is depth-first. That's why we use stack.
# while stack is not empty
while stack:
    # currentdir is popped
    currentdir = stack.pop()
    # if the path popped is not a directory
    if not os.path.isdir(currentdir):
        # print error message not terminating the program
        print(currentdir + " is not a valid directory name.\n")
        continue
    # make currentdir absolute path
    currentdir = os.path.abspath(currentdir)
    # find contents of currentdir
    dircontents = os.listdir(currentdir)
    # iterate through the contents of currentdir
    for name in dircontents:
        # currentitem holds absolute path of current content of currentdir
        currentitem = currentdir + "/" + name
        # if currentitem is a directory
        if os.path.isdir(currentitem):
            # then add it to stack
            stack.append(currentitem)
        # if currentitem is not a directory
        else:
            # update total number of files visited
            statistics['files_visited'] += 1
            # update size of files visited
            statistics['size_of_visited'] += os.stat(currentitem).st_size
            # bool_option holds the logic operation resulted by calling traverse functions on the currentitem and
            # anding them to each other
            bool_option = True
            for pair in traverse_fncs:
                if pair[1]:
                    # calling every traverse function on current item, ANDing the results
                    bool_option = bool_option and pair[0](currentitem)
                # if bool_option is False once, then stop iterating through traverse functions
                if not bool_option:
                    break

# if zip option is given zip the files in the filelist
if args.zip: zip()
# if -nofilelist option is not given, then print the files that satisfy the options
if not args.nofilelist:
    # list the files
    for file in filelist: print(file)
    # if -duplcont or duplname option is given, the above for loop will 
    # not print anything instead we should print the values of dupl_dict
    if args.duplname:
        # the list name_list stores the keys of dupl_dict in sorted order
        name_list = sorted( dupl_dict.keys() )
        # this list iterated so that the files are printed in sorted order according to their
        # file names overall
        for name in name_list: print("\n".join( dupl_dict[name] ), "\n------")
    elif args.duplcont:
        # in the case of -duplcont option files are printed in sorted order of file names within
        # each duplicate set
        for files in dupl_dict.values(): 
            # the anonymous function extract file name from filepaths so that files are sorted according to their file names
            print("\n".join(sorted(files,key=lambda filepath: re.search(r'^(?:.*/|/.*/)(.+)$', filepath).group(1))), "\n------")
#print statistics at the end if -stats option is given
if args.stats: stats()
