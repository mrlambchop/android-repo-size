import os, string, sys, shutil
from subprocess import call
import csv

#Function to check file counts per directory
#
#find ./ -type f | grep -E ".*\.[a-zA-Z0-9]*$" | sed -e 's/.*\(\.[a-zA-Z0-9]*\)$/\1/' | sort | uniq -c | sort -n

#android_branches = [ 'android-1.5r4', 'android-1.6_r2', 'android-2.1_r2.1s', 'android-2.2.3_r2.1', 'android-2.3.7_r1', 'android-4.0.4_r2.1', 'android-4.1.2_r1', 'android-4.2.2_r1' ]
#android_name = [ 'cupcake', 'donut', 'eclair', 'froyo', 'gingerbread', 'icecream-sandwidth', 'jellybean 4.1', 'jellybean 4.2' ]

android_branches = [ 'android-1.6_r2', 'android-2.1_r2.1s', 'android-2.2.3_r2.1', 'android-2.3.7_r1', 'android-4.0.4_r2.1', 'android-4.1.2_r1', 'android-4.2.2_r1' ]
android_name = [ 'donut', 'eclair', 'froyo', 'gingerbread', 'icecream-sandwidth', 'jellybean 4.1', 'jellybean 4.2' ]

cloc_columns = [ 'files', 'language', 'blank', 'comment', 'code' ]
cloc_columns_minus_lang = list(cloc_columns)
cloc_columns_minus_lang.remove('language')

classification = [ 'native', 'build_and_tools', 'framework', 'apps', 'dev' ]

file_types = [ 'java', 'native', 'build_scripts', 'xml' ]

#classification for the top level directories
native = [ 'abi', 'bionic', 'external', 'bootable', 'hardware', 'system' ]
build_and_tools = [ 'build', 'device', 'prebuilt', 'prebuilts', 'vendor' ]
framework = [ 'development', 'dalvik', 'frameworks', 'libcore', 'libnativehelper' ]
apps = [ 'packages' ]
dev = [ 'cts', 'ndk', 'pdk', 'gdk', 'docs', 'sdk' ]

def CheckoutRepo( path, branch ):
   shutil.rmtree(path, True )
   os.makedirs(path)
   
   os.chdir(path)

   cmd = "repo init -u https://android.googlesource.com/platform/manifest -b " + branch
   os.system( cmd )

   cmd = "repo sync"
   os.system( cmd )


def StripGitRepos( path ):

   os.chdir(path)

   #get the big guy first...
   shutil.rmtree( ".repo" )

   #now lets prune all the individual git repos
   for root, dirs, files in os.walk(path):
      for name in dirs:
         if '.git' in name:
            p = os.path.join(root, name)
            print "Deleteing: ", p
            shutil.rmtree( p )


def HighLevelDirs( path ):
   out = []
   for item in os.listdir(path):
      if os.path.isdir(os.path.join(path, item)):
         out.append( item )
   return out


def ParseClocResults( filename ):   
    #create a dict for the 4 columns

    d = {}
    for f in cloc_columns:
       d[f] = []

    #read the data from the CSV file
    dictReader = csv.DictReader(open(filename, 'rb'), fieldnames = cloc_columns, delimiter = ',', quotechar = '"')
    dictReader.next()

    #for each row of the CSV data returned, add to the column dict
    for row in dictReader:
       for key in row:
          try:
             d[key].append(row[key])
          except KeyError: 
             continue

    return d


#returns a Dict with key for the high level directory, the value being a dict of the file types and breakdown (lines, comments etc...)
def CountLinesOfCode( path, branch, high_level_dirs ):
   out = {}

   for d in high_level_dirs:
      if d == "out":
         continue

      dir = path + "/" + d
      tmpfile = dir + ".txt"
      cmd = "cloc " + branch + "/" + d + " --quiet --csv --progress-rate=0 --force-lang=\"make\",mk --report-file=" + tmpfile
      
      #does the directory exist first?
      if os.path.exists( dir ):
         if not os.path.exists( tmpfile ):
            #print cmd
            os.system( cmd )

         o = {}
         if os.path.exists( tmpfile ):
            o = ParseClocResults( tmpfile )
         out[d] = o
      #else:
         #print "Directory doesn't exist: ", dir

   return out


#output dict is a list of src files
def ParseStats( dir_dict, output_dict, stat_type ):

   if len(dir_dict) == 0:
      return

   language = dir_dict['language']

   java_l = [ 'Java' ] #'Javascript'
   native_l = [ 'C++', 'C/C++ Header', 'C', 'Assembly' ]
   build_scripts_l = [ 'Python', 'make', 'Bourne Shell', 'Bourne Again Shell' ]
   xml_l = [ 'XML' ]

   d = dir_dict[ stat_type ]

   for c, l in enumerate(language):
      if l in java_l:
         output_dict['java'] = output_dict['java'] + int(d[c])
      elif l in native_l:
         output_dict['native'] = output_dict['native'] + int(d[c])
      elif l in build_scripts_l:
         output_dict['build_scripts'] = output_dict['build_scripts'] + int(d[c])
      elif l in xml_l:
         output_dict['xml'] = output_dict['xml'] + int(d[c])


#Generate statistics per branch
#Outputs coarse data for 5 catagories, code/comments/num files
def GenerateStats( branch_names, branch_stats ):
   out = {}

   for branch in branch_names:
      branch_summary = {}
      branch_dir_stats = branch_stats[branch]

      for type in cloc_columns_minus_lang:

         native_d = {'java': 0, 'native': 0, 'build_scripts': 0, 'xml': 0}
         build_and_tools_d = {'java': 0, 'native': 0, 'build_scripts': 0, 'xml': 0}
         framework_d = {'java': 0, 'native': 0, 'build_scripts': 0, 'xml': 0}
         apps_d = {'java': 0, 'native': 0, 'build_scripts': 0, 'xml': 0}
         dev_d = {'java': 0, 'native': 0, 'build_scripts': 0, 'xml': 0}

         for dir in branch_dir_stats:
            if dir in native:
               ParseStats( branch_dir_stats[dir], native_d, type )
            elif dir in build_and_tools:
               ParseStats( branch_dir_stats[dir], build_and_tools_d, type )
            elif dir in framework:
               ParseStats( branch_dir_stats[dir], framework_d, type )
            elif dir in apps:
               ParseStats( branch_dir_stats[dir], apps_d, type )
            elif dir in dev:
               ParseStats( branch_dir_stats[dir], dev_d, type )

         stats = {}
         stats['native'] = native_d
         stats['build_and_tools'] = build_and_tools_d
         stats['framework'] = framework_d
         stats['apps'] = apps_d
         stats['dev'] = dev_d

         #print branch, type, stats

         branch_summary[type] = stats

      out[branch] = branch_summary

   return out


def CalcNum( stats, type ):

   branch_summary = {}

   for branch in stats:
      branch_summary[branch] = 0
      bstats = stats[branch] #actual stats for this branch

      type_stats = bstats[type]

      for c in classification: #iterate over the branch stats, per coarse grouping
         tmp = type_stats[c]
         if len(tmp) > 0:
            for f in file_types:
               branch_summary[branch] = branch_summary[branch] + tmp[f]

   return branch_summary



##################
## Main
#################
def main():

   #assume that this is run from a directory where the android repos will be checked out
   initial_path = os.getcwd()

   #checkout the branches only if they don't exist already
   for branch in android_branches:
      branch_path = initial_path + "/" + branch
      print branch_path

      if not os.path.exists( branch_path ):
         print "Branch does not exist - creating"
         CheckoutRepo( branch_path, branch )
         StripGitRepos( branch_path ) #this is just to save space

   #get all the top level dirs from the last branch checked out
   last_branch_path = initial_path + "/" + android_branches[-1]
   high_level_dirs = HighLevelDirs( last_branch_path )
   high_level_dirs.append('vendor')
   high_level_dirs.append('prebuilt')

   #get all the lines of code from each branch
   branch_stats = {}
   for branch in android_branches:
      branch_path = initial_path + "/" + branch
      os.chdir( initial_path )
      branch_stats[ branch ] = CountLinesOfCode( branch_path, branch, high_level_dirs )

   #branch_stats is a dict of dicts, as follows
   #key  [ Android branch ]
   #value[      key  [ Directory in the Android tree ] ]
   #            value[       key  [ column from cloc - files, code etc... ] ]
   #                         value[ list() of counts, keyed from 'language' column ]

   #generate the stats
   processed_stats = GenerateStats( android_branches, branch_stats )

   #stats calc
   for c in cloc_columns_minus_lang:
      print "Type: ", c
      print CalcNum( processed_stats, c )


#usual python main thing
if __name__ == "__main__":
    sys.exit(main())
