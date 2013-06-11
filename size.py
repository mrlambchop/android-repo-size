import os, string, sys, shutil
from subprocess import call
import csv
import collections

remove_xml = True

#Function to check file counts per directory
#
#find ./ -type f | grep -E ".*\.[a-zA-Z0-9]*$" | sed -e 's/.*\(\.[a-zA-Z0-9]*\)$/\1/' | sort | uniq -c | sort -n

#android_branches = [ 'android-1.5r4', 'android-1.6_r2', 'android-2.1_r2.1s', 'android-2.2.3_r2.1', 'android-2.3.7_r1', 'android-4.0.4_r2.1', 'android-4.1.2_r1', 'android-4.2.2_r1' ]
#android_name = [ 'cupcake', 'donut', 'eclair', 'froyo', 'gingerbread', 'icecream-sandwidth', 'jellybean 4.1', 'jellybean 4.2' ]

android_branches = [ 'android-1.6_r2', 'android-2.1_r2.1s', 'android-2.2.3_r2.1', 'android-2.3.7_r1', 'android-4.0.4_r2.1', 'android-4.1.2_r1', 'android-4.2.2_r1' ]
android_name = [ 'donut', 'eclair', 'froyo', 'gingerbread', 'icecream-sandwidth', 'jellybean 4.1', 'jellybean 4.2' ]

#high level dirs
high_level_dirs = ['development', 'external', 'abi', 'bionic', 'sdk', 'gdk', 'cts', 'libnativehelper', 'system', 'libcore', 'docs', 'prebuilts', 'dalvik', 'pdk', 'packages', 'bootable', 'build', 'ndk',  'frameworks', 'vendor', 'prebuilt', 'device', 'hardware']

device_android = ['common', 'generic', 'google', 'sample' ]
device_vendor = ['asus', 'lge', 'samsung', 'ti', 'moto', 'htc' ]

hardware_android = ['libhardware', 'libhardware_legacy', 'ril' ]
hardware_vendor = ['broadcom', 'invensense', 'msm7k', 'qcom', 'samsung_slsi', 'ti' ]

#CLOC
cloc_columns = [ 'files', 'language', 'blank', 'comment', 'code' ]

cloc_columns_minus_lang = list(cloc_columns)
cloc_columns_minus_lang.remove('language')

cloc_columns_minus_lang_files = list(cloc_columns_minus_lang)
cloc_columns_minus_lang_files.remove('files')

#My types
classification = [ 'native', 'build_and_tools', 'framework', 'apps', 'dev' ]

file_types = [ 'java', 'native', 'build_scripts', 'xml' ]

#classification for the top level directories
external = [ 'external', 'prebuilt', 'prebuilts' ]
native = [ 'abi', 'bionic', 'bootable', 'hardware', 'system' ]
build_and_tools = [ 'build', 'pdk', 'device', 'vendor' ]
framework = [ 'development', 'dalvik', 'frameworks', 'libcore', 'libnativehelper' ]
apps = [ 'packages' ]
dev = [ 'cts', 'ndk', 'gdk', 'docs', 'sdk' ]

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
         if remove_xml == False:
            output_dict['xml'] = output_dict['xml'] + int(d[c])


#Generate statistics per branch
#Outputs coarse data for 5 catagories, code/comments/num files
def ClassifyStats( branch_stats ):
   out = {}

   for branch in branch_stats:
      branch_summary = {}
      branch_dir_stats = branch_stats[branch]

      for type in cloc_columns_minus_lang:

         native_d = {'java': 0, 'native': 0, 'build_scripts': 0, 'xml': 0}
         build_and_tools_d = {'java': 0, 'native': 0, 'build_scripts': 0, 'xml': 0}
         framework_d = {'java': 0, 'native': 0, 'build_scripts': 0, 'xml': 0}
         apps_d = {'java': 0, 'native': 0, 'build_scripts': 0, 'xml': 0}
         dev_d = {'java': 0, 'native': 0, 'build_scripts': 0, 'xml': 0}
         external_d = {'java': 0, 'native': 0, 'build_scripts': 0, 'xml': 0}

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
            elif dir in external:
               ParseStats( branch_dir_stats[dir], external_d, type )

         stats = {}
         stats['native'] = native_d
         stats['build_and_tools'] = build_and_tools_d
         stats['framework'] = framework_d
         stats['apps'] = apps_d
         stats['dev'] = dev_d
         stats['external'] = external_d

         #print branch, type, stats

         branch_summary[type] = stats

      out[branch] = branch_summary

   return out


##################
## Calculate summary stats for all classifications of files
#key  [ Directory in the Android tree ] ]
#value[       key  [ column from cloc - files, code etc... ] ]
#             value[ list() of counts, keyed from 'language' column ]
#################
def CalcSummaryByType( stats, type ):

   branch_summary = {}
   count = 0

   for d in stats:
      branch_summary[d] = 0
      cloc_col = stats[d] #actual stats for this branch

      cloc_list = cloc_col[type]

      for c in cloc_list:
         count = count + int(c)

   return count


def PrintSummaryOfDirs( dirs ):
   for d in dirs:
      count = 0
      cloc_col = dirs[d]
      for c in cloc_columns_minus_lang_files:
         for l in cloc_col[c]:
            count = count + int(l)
      print d + "," + str(count)


def PrintSummaryOfFilesBlankCommentCode( branch_stats ):
   print ",Files,Code,Blank,Comments"
   for b in branch_stats:
      files_stats = CalcSummaryByType( branch_stats[b], "files" )
      blank_stats = CalcSummaryByType( branch_stats[b], "blank" )
      comment_stats = CalcSummaryByType( branch_stats[b], "comment" )
      code_stats = CalcSummaryByType( branch_stats[b], "code" )
      print b + "," + str(files_stats) + "," + str(blank_stats) + "," + str(comment_stats) + "," + str(code_stats)

   #classified_stats is a dict of dicts, as follows
   #key  [ Android branch ]
   #value[      key  [ Stats type - files, blank, comment, code ] ]
   #            value[              key  [ Classification - native, build_and_tools, framework, apps, dev ]
   #                                value[              key  [ file types - xml, build_scripts, java, native ] ]
   #                                                    value[ count ]
def PrintClassifiedStats( stats ):
   print "/nClassified statistics\n"
   print ",xml,build_scripts,java,native"
   for branch in stats:
      stats_type = stats[branch]      
      stats_code = stats_type['code']
      print branch,
      count = 0
      xml = 0
      build_scripts = 0
      java = 0
      native = 0
      for classification in stats_code:
         file_types = stats_code[classification]
         xml = xml + int(file_types['xml'])
         build_scripts = build_scripts + int(file_types['build_scripts'])
         java = java + int(file_types['java'])
         native = native + int(file_types['native'])
      print ",", xml, ",", build_scripts, ",", java, ",", native


   print "/nClassified statistics\n"
   #print ",build_and_tools,apps,dev,framework,external,native"
   b = stats['android-1.6_r2']
   c = b['code']
   for d in stats_code: print ",", d,
   print ""

   for branch in stats:
      stats_type = stats[branch]
      stats_code = stats_type['code']
      print branch,
      for classification in stats_code:
         file_types = stats_code[classification]
         count = 0
         for f in file_types:
            count = count+ int(file_types[f])
         print ",", count,
      print ""




   print "/nClassified statistics - comments\n"
   #print ",build_and_tools,apps,dev,framework,external,native"
   b = stats['android-1.6_r2']
   c = b['comment']
   for d in stats_code: print ",", d,
   print ""

   for branch in stats:
      stats_type = stats[branch]
      stats_code = stats_type['comment']
      print branch,
      for classification in stats_code:
         file_types = stats_code[classification]
         count = 0
         for f in file_types:
            count = count+ int(file_types[f])
         print ",", count,
      print ""



##################
## Main
#################
def main():

   #assume that this is run from a directory where the android repos will be checked out
   initial_path = os.getcwd()

   #checkout the branches only if they don't exist already
   for branch in android_branches:
      branch_path = initial_path + "/" + branch

      if not os.path.exists( branch_path ):
         print "Branch does not exist - creating"
         CheckoutRepo( branch_path, branch )
         StripGitRepos( branch_path ) #this is just to save space

   #get all the top level dirs from the last branch checked out
   #last_branch_path = initial_path + "/" + android_branches[-1]
   #high_level_dirs = HighLevelDirs( last_branch_path )
   #high_level_dirs.append('vendor')
   #high_level_dirs.append('prebuilt')
   #if 'out' in high_level_dirs:
   #   high_level_dirs.remove('out')

   all_device_dirs = high_level_dirs

   #get all the lines of code from each branch
   branch_stats = collections.OrderedDict()
   for branch in android_branches:
      branch_path = initial_path + "/" + branch
      os.chdir( initial_path )
      branch_stats[ branch ] = CountLinesOfCode( branch_path, branch, high_level_dirs )

   #branch_stats is a dict of dicts, as follows
   #key  [ Android branch ]
   #value[      key  [ Directory in the Android tree ] ]
   #            value[       key  [ column from cloc - files, code etc... ] ]
   #                         value[ list() of counts, keyed from 'language' column ]

   #print a little table summary of the 4 sections
   print "Summary of high level projects for all directories\n"
   PrintSummaryOfFilesBlankCommentCode( branch_stats )

   #directory summary, currently per branch
   print("android-4.2.2_r1:\n")
   PrintSummaryOfDirs( branch_stats[ 'android-4.2.2_r1' ] )

   print("android-4.1.2_r1:\n")
   PrintSummaryOfDirs( branch_stats[ 'android-4.1.2_r1' ] )

   #classify the statistics into high level groups, ignoring
   classified_stats = ClassifyStats( branch_stats )

   #classified_stats is a dict of dicts, as follows
   #key  [ Android branch ]
   #value[      key  [ Stats type - files, blank, comment, code ] ]
   #            value[              key  [ Classification - native, build_and_tools, framework, apps, dev ]
   #                                value[              key  [ file types - xml, build_scripts, java, native ] ]
   #                                                    value[ count ]

   PrintClassifiedStats( classified_stats )


#usual python main thing
if __name__ == "__main__":
    sys.exit(main())
