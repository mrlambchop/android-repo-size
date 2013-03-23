import os, string, sys, shutil
from subprocess import call
import csv

#android_branches = [ 'android-1.5r4', 'android-1.6_r2', 'android-2.1_r2.1s', 'android-2.2.3_r2.1', 'android-2.3.7_r1', 'android-4.0.4_r2.1', 'android-4.1.2_r1', 'android-4.2.2_r1' ]
#android_name = [ 'cupcake', 'donut', 'eclair', 'froyo', 'gingerbread', 'icecream-sandwidth', 'jellybean 4.1', 'jellybean 4.2' ]

android_branches = [ 'android-1.6_r2', 'android-2.1_r2.1s', 'android-2.2.3_r2.1', 'android-2.3.7_r1', 'android-4.0.4_r2.1', 'android-4.1.2_r1', 'android-4.2.2_r1' ]
android_name = [ 'donut', 'eclair', 'froyo', 'gingerbread', 'icecream-sandwidth', 'jellybean 4.1', 'jellybean 4.2' ]

def PrintBranchNameInfo():
   for count,branch in enumerate( android_branches ):
      print branch, android_name[count]

def CreateDirectory( path ):
   shutil.rmtree(path, True )
   os.makedirs(path)

def CheckoutRepo( path, branch ):
   CreateDirectory( path )
   
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
    fields = [ 'files', 'language', 'blank', 'comment', 'code' ]  
    #fields = [ "XML", "Java", "C++", "HTML", "C/C++ Header", "C", "Python", "Javascript", "Assembly", "make", "Bourne Shell", "Bourne Again Shell" ]

    d = {}
    for f in fields:
       d[f] = []

    dictReader = csv.DictReader(open(filename, 'rb'), fieldnames = fields, delimiter = ',', quotechar = '"')
    dictReader.next()

    for row in dictReader:
       for key in row:
          try:
             d[key].append(row[key])
          except KeyError: 
             continue

    return d


def CountLinesOfCode( path, branch, high_level_dirs ):
   out = {}
   for d in high_level_dirs:
      tmpfile = path + "/" + d + ".txt"
      cmd = "cloc " + branch + "/" + d + " --quiet --csv --progress-rate=0 --report-file=" + tmpfile
      print cmd
      
      if not os.path.exists( tmpfile ):
         os.system( cmd )

      o = {}
      if os.path.exists( tmpfile ):
         o = ParseClocResults( tmpfile )
      out[d] = o

   return out


#####

PrintBranchNameInfo()

initial_path = os.getcwd()

#checkout the branches
for branch in android_branches:
   branch_path = initial_path + "/" + branch
   print branch_path

   if not os.path.exists( branch_path ):
      print "Branch does not exist - creating"
      CheckoutRepo( branch_path, branch )
      StripGitRepos( branch_path ) #this is just to save space

#get all the top level dirs from the last branch
last_branch_path = initial_path + "/" + android_branches[-1]
high_level_dirs = HighLevelDirs( last_branch_path )

#get the common
for branch in android_branches:
   branch_path = initial_path + "/" + branch
   os.chdir( initial_path )
   output = CountLinesOfCode( branch_path, branch, high_level_dirs )
   print output
