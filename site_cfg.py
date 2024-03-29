# site_cfg.py
# http://sites.google.com/site/pocketsense/
# define class to read and hold user-defined parameters
# including sites, funds and stocks

# Intial version: rlc: Feb-2010

# History
# ---------
# 01Mar2009*rlc
#   - Modified to include additional data fields (appid, appver, and brokerid).
# 09Sep2010*rlc
#   - Add support for alternate Yahoo! quote site URLs
# 27Dec2010*rlc
#   - Removed support the old control.py control file
# 04Jan2010*rlc
#   - Use DefaultAppID and DefaultAppVer from control2
#   - Add support for Quote html flags (show file after download)
# 18Feb2011*rlc
#   - Added support for YahooTimeZone, yahooScrape, quote currency, timeoffset (site), and quote multiplier
# 22Mar2011*rlc:
#   - Added support for alternate ticker symbol to send to Money (instead of Yahoo symbol)
# 28Aug2012*rlc:
#   - Added support for OFX version 103 and ClientUID
#   - Added support for combineOFX
#   - Added quietScrub option.  Default = No
# 28Aug2013*rlc:
#   - Added support for forceQuotes option
# 21Oct2013*rlc:
#   - Added support for QuoteAccount option
# 19Jan2014*rlc:
#   -Added EnableGoogleFinance option
# 14Aug2016*rlc:
#   -make accttype ucase
# 11Mar2017*rlc:
#   -remove ClientUID from general settings.  begin storing per site+username in ofx.py
# 27Aug2017*rlc
#   -explicitly match stock/fund multiplier as <space>m:value, requiring the space
# 09Oct2017*rlc
#   -change to use Yahoo json quote api
#   -remove enableYahooScrape option
# 06Dec2017*rlc
#   -add GoogleURL as sites.dat option
# 07Mar2020*rlc
#   -disable Google Finance by default, and disable setting
# 15Feb2021*rlc
#   -add support for site-specific skipZeroTrans option
#   -add support for the following site parameters: dtacctup, useragent, clientuid, skipzerotrans
# 10Mar2021*rlc
#   - add support for promptStart and promptEnd parameters in sites.dat
# 25May2023*rlc
#   -change YahooURL for new v10 service
# 17Jul2023*rlc
#   -remove reference to google finance.  not supported

import os, glob, re, random
from rlib1 import *
from control2 import *

class site_cfg:
    """read-in site and ticker data from sites.dat and define the data structures used by ofx.py"""

    #NOTE:  This function will capitalize the user-defined name for an institution, but not the site contents.
    #       Site information, including the URL and identifiers *may be case sensitive*, so we have to
    #       preserve case for the OFX fields.

    #******************************************************************************
    # NOTE:
    #   The parse routine separates the user site list into
    #   a Python DICT format that looks like the following:
    #       Sites = {
    #               "UNIVERSAL_ATT": {
    #                    "caps": [ "SIGNON", "CCSTMT" ],
    #                   "fiorg": "Citigroup",
    #                     "fid": "24909",
    #                     "url": "https://secureofx2.bankhost.com/citi/cgi-forte/ofx_rt?servicename=ofx_rt&pagename=ofx",
    #                     field: value,
    #                            etc...
    #               },
    #               "site2": {...}
    #               }
    #
    #   Stocks are parsed into a list named stocks[].  Funds go into funds[], although there is really no difference.
    #******************************************************************************

    def __init__(self):
        #do we have a sites data file?  if so, read it in
        #if not, try to create a new one from either a backup or template file

        #vars defined in the __init__ function are *private* for each instance.
        #vars defined at the Class level are shared among all instances!  rlc
        self.sites = {}
        self.stocks= []
        self.funds = []
        self.defaultInterval = 7
        self.promptInterval=False
        self.YahooURL = 'https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=price'
        self.GoogleURL = 'http://www.google.com/finance/quote'
        self.datfile= 'sites.dat'
        self.bakfile= 'sites.bak'
        self.tmplfile = 'sites.template'
        self.savetickersfirst = False
        self.savequotehistory = False
        self.showquotehtm = False
        self.askquotehtm = False
        self.YahooTimeZone = '-5:EST'
        self.quotecurrency = 'USD'
        self.combineofx = False
        self.quietScrub = False
        self.forceQuotes = False
        self.quoteAccount = '0123456789'
        self.enableYahooFinance = True
        self.skipZeroTransactions = False
        self.skipFailedLogon = True
        self.promptStart = True
        self.promptEnd   = False

        if glob.glob(self.datfile) == []:
            if glob.glob(self.bakfile) != []:
                #we have a backup file... make it our dat file
                copy_txt_file(self.bakfile, self.datfile)
            elif glob.glob(self.tmplfile) != []:
                #we have a template file... make it our dat file
                copy_txt_file(self.tmplfile, self.datfile)

        if glob.glob(self.datfile) != []:
            self.load_cfg()

    def load_cfg(self):
        #read in sites.dat
        self.load_sites()
        self.load_stocks()
        self.load_funds()

    def load_sites(self):
        f = open(self.datfile, 'r')
        parsing = False

        #find each <site> entry and read-in the parameters
        for line in f:
            line  = self.clean_line(line)    #remove comments, spaces, tabs, newlines, etc
            lineU = line.upper()

            #reset parameters between sites
            if not parsing:
                sitename=''
                accttype=''
                fiorg=''
                fid =''
                url=''
                bankid=''
                brokerid=''
                ofxver = '102'
                appid  = DefaultAppID       #defined in control2.py
                appver = DefaultAppVer
                mininterval = 0
                timeOffset = 0.0
                delay = 0.0
                dtacctup = None
                skipzerotrans = None
                useragent = None
                clientuid = None

            if '<SITE>' in lineU:
                parsing = True

            if '</SITE>' in lineU:
                parsing = False    #end parsing site
                if sitename != '' and url != '':
                    X = {sitename: {
                               'CAPS': ['SIGNON', accttype],
                              'FIORG': fiorg,
                                'URL': url,
                                'FID': fid,
                             'BANKID': bankid,
                           'BROKERID': brokerid,
                             'OFXVER': ofxver,
                              'APPID': appid,
                             'APPVER': appver,
                        'MININTERVAL': mininterval,
                         'TIMEOFFSET': timeOffset,
                              'DELAY': delay,
                      'SKIPZEROTRANS': skipzerotrans,
                           'DTACCTUP': dtacctup,
                          'USERAGENT': useragent,
                          'CLIENTUID': clientuid}
                        }
                    self.sites.update(X)

            #parse the site parameters for the current site
            field = self.get_fieldname(line).upper()
            value = self.get_paramval(line)

            if value:
                if parsing:
                    if field == 'SITENAME': sitename = value.upper()
                    elif field == 'ACCTTYPE': accttype = value.upper()
                    elif field == 'FIORG': fiorg = value
                    elif field == 'FID': fid = value
                    elif field == 'URL': url = value
                    elif field == 'BANKID': bankid = value
                    elif field == 'BROKERID': brokerid = value
                    elif field == 'OFXVER': ofxver = value
                    elif field == 'APPID': appid = value
                    elif field == 'APPVER': appver = value
                    elif field == 'MININTERVAL': mininterval = int(value)
                    elif field == 'TIMEOFFSET': timeOffset = float(value)
                    elif field == 'DELAY': delay = float(value)
                    elif field == 'SKIPZEROTRANS': skipzerotrans = True if 'Y' in value else False if 'N' in value else None
                    elif field == 'DTACCTUP': dtacctup = value
                    elif field == 'USERAGENT': useragent = value
                    elif field == 'CLIENTUID': clientuid = value

                else:
                    #look for individual parameters while we're NOT parsing site info
                    if field == 'DEFAULTINTERVAL':
                        self.defaultInterval = int2(value)

                    if field == 'PROMPTINTERVAL':
                        self.promptInterval = (value[:1].upper() == 'Y')

                    if field == 'SAVETICKERSFIRST':
                        self.savetickersfirst = (value[:1].upper() == 'Y')

                    if field == 'SAVEQUOTEHISTORY':
                        self.savequotehistory = (value[:1].upper() == 'Y')

                    if field == 'SHOWQUOTEHTM':
                        self.showquotehtm = (value[:1].upper() == 'Y')

                    if field == 'ASKQUOTEHTM':
                        self.askquotehtm = (value[:1].upper() == 'Y')

                    if field == 'ENABLEYAHOOFINANCE':
                        self.enableYahooFinance = (value[:1].upper() == 'Y')

                    if field == 'YAHOOURL':
                        self.YahooURL = value

                    if field == 'YAHOOTIMEZONE':
                        self.YahooTimeZone = value

                    if field == 'GOOGLEURL':
                        self.GoogleURL = value

                    if field == 'QUOTECURRENCY':
                        self.quotecurrency = value

                    if field == 'COMBINEOFX':
                        self.combineofx = (value[:1].upper() == 'Y')

                    if field == 'QUIETSCRUB':
                        self.quietScrub = (value[:1].upper() == 'Y')

                    if field == 'FORCEQUOTES':
                        self.forceQuotes = (value[:1].upper() == 'Y')

                    if field == 'QUOTEACCOUNT':
                        self.quoteAccount = value

                    if field == 'SKIPZEROTRANSACTIONS':
                        self.skipZeroTransactions = (value[:1].upper() == 'Y')

                    if field == 'SKIPFAILEDLOGON':
                        self.skipFailedLogon = (value[:1].upper() == 'Y')

                    if field == 'PROMPTSTART':
                        self.promptStart = (value[:1].upper() == 'Y')

                    if field == 'PROMPTEND':
                        self.promptEnd = (value[:1].upper() == 'Y')

           #end_for line

        f.close()

        if self.askquotehtm: self.showquotehtm = False  #can't have both.  Asking overrides "always"

        return

    def load_stocks(self):
        f = open(self.datfile, 'r')
        parsing = False

        #find each stock entry and read-in the parameters
        for line in f:
            line = line.upper()
            line = self.clean_line(line)

            if '<STOCKS>' in line:
                parsing = True

            elif '</STOCKS>' in line:
                parsing = False

            elif parsing and len(line) > 0:
                entry = self.parseTicker(line)
                if entry['ticker'] != "err":
                    self.stocks.append(entry)
        #end_for

        f.close()
        return

    def load_funds(self):
        f = open(self.datfile, 'r')
        parsing = False

        #find each stock entry and read-in the parameters
        for line in f:
            line = line.upper()
            line = self.clean_line(line)

            if '<FUNDS>' in line:
                parsing = True

            elif '</FUNDS>' in line:
                parsing = False

            elif parsing and len(line) > 0:
                entry = self.parseTicker(line)
                if entry['ticker']  != "err":
                    self.funds.append(entry)
        #end_for

        f.close()
        return

    def parseTicker(self, line):
        t = re.compile("(.+?) ")         #ticker symbol is first option
        m = re.compile(" M:(.+?) ")      #multiplier option
        s = re.compile(" S:(.+?) ")      #symbol to pass to Money (optional)
        line += " "                      #pad a space onto the end for re.search
        tr = t.search(line)
        mr = m.search(line)
        sr = s.search(line)
        if tr: ticker=tr.group(1)
        else: ticker = "err"
        if mr: multiplier=float2(mr.group(1))
        else: multiplier = 1.0
        if sr: symbol=sr.group(1)
        else: symbol = ticker
        return {'ticker': ticker, 'm': multiplier, 's': symbol}

    def clean_line(self, line):
        #remove comments
        i = line.find('#')
        if i > -1:
            line = line[:i]
        #remove newlines, tabs, commas and leading/trailing
        line = line.replace('\n','')
        line = line.replace('\t','')
        line = line.replace(',','')
        line = line.rstrip().lstrip()
        return line

    def get_paramval(self, line):
        #get the value for a field : value pair in line
        val = line[line.find(':')+1:]
        #remove trailing/leading spaces and newlines
        return val.lstrip().rstrip()

    def get_fieldname(self, line):
        #get the field name from a field : value pair in line
        val = line[ : line.find(':')]   #everything to the left of 1st colon
        #remove trailing/leading spaces, tabs, newlines
        return val.lstrip().rstrip()

    def get_intval(self, line):
        strval = self.get_paramval(line)
        if strval == '':
            intval = 0
        else:
            intval = int(strval)
        return intval
