import sys, datetime, csv, shutil, os, re
import argparse
import collections

DESCRIPTION_SHORT = """Tool to create DDR files import CSV from CSUJAD data."""

DESCRIPTION_LONG = """
Uses CSUJAD CONTENTdm CSV file and directory of binary files to create a CSV 
file for DDR import.

USAGE
$ ddr-csujadconvert-files DDR_COLLECTION_BASE FILE_ROLE CSUJAD_CSV_INPUT_FILE CSUJAD_BINARY_DIRECTORY DDR_CSV_OUTPUT_BASE_PATH
$ ddr-csujadconvert-files ddr-csujad-1 master ./raw/csujaddata.csv ./binaries/preservation ./transformed
---"""

# Support functions

def load_data(csvpath):
    csvfile = open(csvpath, 'rb')
    csvreader = csv.DictReader(csvfile)
    data = []
    for row in csvreader:
        data.append(row)
    return data

def build_dict(seq, key):
    return dict((d[key], dict(d, index=index)) for (index, d) in enumerate(seq))

def write_log(message):
    logfile = open(LOGFILE,'a')
    logfile.write(message + "\n")
    logfile.close()
    return

#TODO make this work for other edge cases!!
def parse_csufilename(rawfilename):
    #remove file extension
    rawlocalid = rawfilename[:rawfilename.rfind('.')]
    fsort = '1'
    #detect 'ike_01_01_003_Part3.pdf'
    if '_Part' in rawlocalid:
        localid = rawlocalid[:rawlocalid.rfind('_')]
        fsort = rawlocalid[rawlocalid.rfind('t') + 1:]
    #detect 'ike_05_23_012b.jpg'
    elif rawlocalid.rstrip()[-1].isalpha():
        localid = rawlocalid[:-1]
        fsort = str(ord(rawlocalid.rstrip()[-1]) - 96)
    #detect 'nis_05_035_174_0001.tif' where localid == 'nis_05_035_174'
    #CSU_LOCALID_PARTS = number of _ separated parts in localid
    elif len(rawlocalid.split('_')) > CSU_LOCALID_PARTS:
        localid = rawlocalid[:rawlocalid.rfind('_')]
        fsort = int(rawlocalid[rawlocalid.rfind('_'):])
    else:
        localid = rawlocalid
    return localid, fsort

def get_csufiles(csubinpath):
    csufiles_ = []
    for root, dirs, files in os.walk(csubinpath):
        for file_ in files:
            #remove hidden/system files
            if file_.startswith('.'):
                continue
            #print 'processing file: {}'.format(file_)
            csufile_ = collections.OrderedDict.fromkeys(['csu_localid','csu_filename','csu_filesort'])
            fsort = '1'
            csufile_['csu_filename'] = file_
            csufile_['csu_localid'], csufile_['csu_filesort'] = parse_csufilename(file_)
            csufiles_.append(csufile_)
    return csufiles_

# Main
LOGFILE = './logs/{:%Y%m%d-%H%M%S}-csujadconvert-files.log'.format(datetime.datetime.now()) 

CSU_FIELDS = ['Local ID', 'Project ID', 'Title/Name', 'Creator', 'Date Created', 'Description', 'Location', 'Facility', 'Subjects', 'Type', 'Genre', 'Language', 'Source Description', 'Collection', 'Collection Finding Aid', 'Collection Description', 'Digital Format', 'Project Name', 'Contributing Repository', 'View Item', 'Rights', 'Notes', 'Object File Name', 'OCLC number', 'Date created', 'Date modified', 'Reference URL', 'CONTENTdm number', 'CONTENTdm file name', 'CONTENTdm file path', 'DDR Rights', 'DDR Credit Text']

# number of '_'-separated parts in collection's 'Local ID'; e.g., 'ike_01_01_006'
CSU_LOCALID_PARTS = 4

DDR_FILES_FIELDS = ['id','external','role','basename_orig','mimetype','public','rights','sort','thumb','label','digitize_person','tech_notes','external_urls','links']

# Get script args
ddridbase = sys.argv[1]
ddrmodel = sys.argv[2]
csucsvpath = sys.argv[3]
csubinpath = sys.argv[4]
try: 
    outputpath = sys.argv[5]
except IndexError:
    outputpath = './'

print '{} : Begin run.'.format(datetime.datetime.now())

# Load data
csudata = load_data(csucsvpath)
print '{} : Raw csv rows to be processed: {}'.format(datetime.datetime.now(), len(csudata))

# Get file names from CSU data
csufiles = get_csufiles(csubinpath)
print '{} : Binary files in input directory: {}'.format(datetime.datetime.now(), len(csufiles))

#print 'csudata first row: {}'.format(csudata[0])
#print 'csudata first row \'Local ID\': {}'.format(csudata[0]['Local ID'])

#init counters
rownum = 0
processedobject = 0
filescreated = 0
partobject = 0

#process each entity row in csu csv
for csuentity in csudata:
    rownum += 1
    #check that row contains an object record; not just part of compound object
    if csuentity['Project ID'] != '':

        outfile = os.path.join(outputpath, '{:%Y%m%d-%H%M}-{}-files.csv'.format(datetime.datetime.now(),ddridbase))
        #write header row if first pass
        if not os.path.isfile(outfile):
            odatafile = open(outfile,'w')
            outwriter = csv.writer(odatafile)
            outwriter.writerow(DDR_FILES_FIELDS)
            odatafile.close()
    
        for csufile in csufiles:
            #find matching file in csufiles; then write some data
            if csuentity['Local ID'] == csufile['csu_localid']:
                #setup row dict
                ddrfilerow = collections.OrderedDict.fromkeys(DDR_FILES_FIELDS)
                #assemble row
                #TODO: less naive DDR ID creation.auto-generate DDR ID
                #ddrfilerow['id'] = get_ddrid(csuentity['Local ID'])
                ddrfilerow['id'] = ddridbase + '-{}'.format(processedobject + 1)
                ddrfilerow['external'] = '0'
                ddrfilerow['role'] = ddrmodel
                ddrfilerow['public'] = '1'
                ddrfilerow['basename_orig'] = csufile['csu_filename']
                ddrfilerow['mimetype'] = csuentity['Digital Format'].split(';')[0].strip()
                ddrfilerow['rights'] = csuentity['DDR Rights']
                ddrfilerow['sort'] = csufile['csu_filesort']
                ddrfilerow['label'] = 'Part {}'.format(csufile['csu_filesort'])
                ddrfilerow['digitize_person'] = ''
                ddrfilerow['tech_notes'] = ''
                ddrfilerow['external_urls'] = ''
                ddrfilerow['links'] = ''
                #write row
                odatafile = open(outfile,'a')
                outwriter = csv.writer(odatafile)
                outwriter.writerow(ddrfilerow.values())
                filescreated +=1
            
        #increment the processed counter and close the output file
        processedobject +=1
        odatafile.close()
    else:
        partobject +=1
        print '{} : Row #{} did not have \'Project ID\'. Looks like a compound object part.'.format(datetime.datetime.now(), rownum)

print '{} : Run ended.'.format(datetime.datetime.now())
print '{} : {} rows processed. {} objects found. {} new file rows created. {} partial object rows discarded.'.format(datetime.datetime.now(), rownum, processedobject, filescreated, partobject)

#end
