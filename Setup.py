#!/usr/bin/env python3

# setup.py
# http://sites.google.com/site/pocketsense/
# setup account info
# Intial version: rlc: Feb-2010

#02Mar2010*rlc
#   - Corrected bug for entering bank statement type (checking/savings)
#   - List account type for all accounts (not just bank types)
#   - Cleaned up formatting a bit
#   - Added Money Market and Credit Line as valid bank account type

# 28Aug2013*rlc
#   - Added support for forceQuotes option

# 19Sep2013*rlc
#   - Single line change to menu text

# 11Mar2017*rlc
#   - Add support for user-specific clientUID keys

# 11May2017*rlc
#   - increase field width for account# to handle yet another Discover change

# 14May2018*rlc
#   - added account query during setup

#23Aug2018*rlc
#   - bug fix w/ adding new account

#16Sep2019*rlc
#   - create ./import folder during setup

#26Apr2020*rlc
#   - minor bug fix (print statement)
#19Jun2023*rlc
#   - add logging

import os, sys, glob, re, pickle, shutil, time
import pyDes, ofx, quotes, site_cfg, filecmp
import rlib1
from control2 import *  #global settings

#startup
print('')
log = rlib1.create_logger('root', 'setup.log')
if Debug:
    log.warning("**DEBUG Enabled: See Control2.py to disable.")
    log.debug('xfrdir = %s' % xfrdir)

#global vars

BankTypes = ['CHECKING', 'SAVINGS', 'MONEYMRKT', 'CREDITLINE']
AcctArray = []
Sites = []

# each account stored as:  acct = [sitename, account, acctype, username, password]

def separator_line(txt='', before=0, after=0):
    w=30
    l=len(txt)
    flen =int((w - l)/2)
    if before > 0: print('\n' * before)
    print('-'*flen + txt + '-'*(w-flen-l))
    if after > 0: print('\n' * after)

def list_accounts(showConnectKeys=False):
    i=1
    print('\n\n')
    print('{0:22}{1:24}{2:14}{3}'.format('Site','Account','Type','UserName'))
    print('-'*70)
    for acct in AcctArray:
        sitename = acct[0]
        account  = acct[1]
        type     = acct[2]
        user     = acct[3]
        if sitename in Sites:
            type = rlib1.FieldVal(Sites[sitename], 'caps')[1]  #default to showing the acctType from sites.dat
            url = rlib1.FieldVal(Sites[sitename],'url')
            ofxVer = rlib1.FieldVal(Sites[sitename], 'ofxver')
            #clientuid can be defined for the site (sites.dat), or for the account (via setup)
            clientUID = rlib1.FieldVal(Sites[sitename], 'clientuid')
            if clientUID is None and rlib1.int2(ofxVer) > 102:
                clientUID = rlib1.clientUID(url, user)
            if   type == 'INVSTMT': type = 'INVESTMENT'
            elif type == 'CCSTMT':  type = 'CREDIT CARD'
            print('{0:4}{1:18}{2:24}{3:14}{4}'.format(str(i)+'.',sitename,account,type,user))
            if showConnectKeys and clientUID!=None:
                print('\t\t      ConnectKey: %s\n' % (clientUID))
        else:
            print('{0:4}{1:18}{2}'.format(str(i)+'.',sitename, '** Site not found in SITES.DAT **'))
        i=i+1

def config_account():

    #configure account settings
    tmpfile='acctQuery.tmp'
    i=1
    separator_line('Site List', 1)
    for site in Sitenames:
        print('%d. %s' % (i, site))
        i=i+1
    print('0. Exit')
    separator_line()
    sitenum = rlib1.get_int('Enter Site #: [0] ')

    if sitenum != 0 and sitenum <= len(Sitenames):
        sitenum = sitenum - 1   #index into array
        sitename = Sitenames[sitenum]
        log.info('Configuring account for %s' % sitename)
        username = input('User name       : ')
        password = input('Account password: ')

        #query server for available (valid) accounts for user
        stat=True
        try:
            log.info('Requesting accounts for %s @ %s' % (username, sitename))
            client = ofx.OFXClient(userdat.sites[sitename], username, password)
            query = client.acctQuery()
            if Debug: log.debug(query)
            client.doQuery(query, tmpfile)
            if not client.status: stat=False
            with open(tmpfile, "r") as f:  response = f.read()
            os.remove(tmpfile)
        except Exception as inst:
            stat=False
            log.exception('An error occurred when executing query')

        if Debug:
            log.debug('**Account query response')
            log.debug(response)

        if not stat or not '<ACCTID>' in response:
            log.warning('An error occurred requesting accounts from the site.  Please check username and password.')
            ans = input('Continue configuring account (Yes/No): [N] ') or 'N'
            stat = True if ans[0].upper() == 'Y' else False

        if stat:
            #list accounts and prompt for entry

            #account numbers may be masked, so we allow actual account numbers too
            print('\n\n*****************')
            print('  NOTE:  If the account number is masked (e.g., XXXX-XX-1234),')
            print('         you must manually enter the actual account number')
            print('*****************\n')
            print('\nEnter line #, *or* the actual account number\n')
            print('\nAccount List')
            print('------------')
            alist = re.findall(r'<ACCTID>(.*?)<', response,         #get list of account entries
                               flags=re.DOTALL | re.IGNORECASE)
            alist = [a.rstrip() for a in alist]                     #strip trailing whitespace/newlines/etc
            alist = sorted(alist)

            i=1
            for a in alist:
                print('%i. %s' % (i, a))
                i+=1

            account  = input('\nAccount #       : ') or 0
            if account==0:
                input("No account selected.  Press <Enter> to return to the main menu")
                return

            if len(account) < 3: account = alist[int(account)-1]

            acctype = ''
            #if this is a bank account, get the type (checking/savings)
            if 'BASTMT' in rlib1.FieldVal(Sites[sitename],'CAPS'):
                selnum = -1
                while selnum < 0 or selnum > len(BankTypes):
                    i = 1
                    separator_line('Type of Bank Account', 1)
                    for type in BankTypes:
                        print('%d. %s' % (i, type))
                        i=i+1

                    print('0. %s' % 'Cancel')
                    separator_line()
                    selnum= rlib1.get_int('Enter account type: [0] ')
                    if selnum == 0: return

                acctype = BankTypes[selnum-1]

            #look for pre-existing entry.  delete if found.
            exists = False
            for acct in AcctArray:
                if acct[0] == sitename and acct[1] == account:
                    #duplicate entry... replace it
                    exists = True
                    AcctArray.remove(acct)
                    break

            if exists:
                log.info('Replacing %s:%s' % (sitename, account))
            else:
                log.info('Adding %s:%s' % (sitename, account))

            acct = [sitename, account, acctype, username, password]
            AcctArray.append(acct)

            #test the new account?
            test = input('Do you want to test transaction downloads for the new account now (y/n)? ').upper()
            if test=='Y':
                log.info('Testing account %s:%s' % (sitename, account))
                test_acct(acct)

def test_acct(acct):
    status, ofxfile = ofx.getOFX(acct, 31)
    if status:
        if ofxfile !='':
            log.info('Download completed successfully')
            test = input('Send the results to Money (y/n)? ').upper()
            if test=='Y':
                rlib1.runFile(ofxfile)
                input('Press Enter to continue...')
            else:
                log.info('Results not sent to Money.  Cancelled by user.')
    else:
        log.warning('An online error occurred while testing the new account.')


def test_quotes():
        status, ofxFile1, ofxFile2, htmFile = quotes.getQuotes()
        if status:
            log.info('Download completed successfully')
            ask = input('Open <Quotes.htm> in the default browser (y/n)?').upper()
            if ask=='Y':
                os.startfile(htmFile)   #don't wait for browser close

            ask = input('Send the results to Money (y/n)? ').upper()
            if ask=='Y':
                if ofxFile2 != '':
                    rlib1.runFile(ofxFile2)
                    if Debug: input('\nPress <Enter> to send ForceQuotes statement.')
                    time.sleep(0.5)      #slight delay, to force load order in Money
                rlib1.runFile(ofxFile1)
                input('Press Enter to continue...')
        else:
            log.warning('An error occurred while testing Stock/Fund quotes.')


#----------------------------------------------------------------------------------------
if __name__=="__main__":

    print('')
    log.info(AboutTitle + ", Ver: " + AboutVersion)

    #keep a backup copy of the sites.dat file
    backup = True
    if glob.glob('sites.dat') != []:
        if glob.glob('sites.bak') != []:
            if filecmp.cmp('sites.bak', 'sites.dat'): backup = False
        if backup: shutil.copy('sites.dat', 'sites.bak')

    #get the user parameters
    userdat = site_cfg.site_cfg()
    Sites = userdat.sites

    #build a Sitenames list one time
    Sitenames = []  #Sitenames array
    for site in Sites:
        Sitenames.append(site)

    Sitenames.sort()

    #do we already have a configuration file?  if so, read it in.
    pwkey, c_getquotes, AcctArray = rlib1.get_cfg()

    #is the file password protected?  If so, we need to get passkey and decrypt the account info
    if len(pwkey):
        pwkey=rlib1.decrypt_pw(pwkey)
        rlib1.acctDecrypt(AcctArray, pwkey)

    #check system config for required folders
    if not os.path.exists(xfrdir):
        try:
            os.mkdir(xfrdir)
        except:
            log.exception('**Could not create %s' % xfrdir)
            system.exit()
    if not os.path.exists(importdir):
        try:
            os.mkdir(importdir)
        except:
            log.exception('**Could not create %s' % importdir)
            system.exit()

    #**********main menu***********
    menu_option = 1
    while menu_option != 0:

        #sort accounts by site+username+account
        AcctArray = sorted(AcctArray, key = lambda x: (x[0], x[3], x[1]))
        if len(pwkey):
            menu_4 = '4. Change Password'
            menu_5 = '5. Remove Encryption'
        else:
            menu_4 = '4. Encrypt account settings'
            menu_5 = ''

        if c_getquotes:
            menu_6 = ('6. Disable Stock/Fund Quotes')
        else:
            menu_6 = ('6. Enable Stock/Fund Quotes')

        separator_line('Main Menu', 1)
        print("1. Add or Modify Account")
        print("2. List Accounts")
        print("3. Delete Account (or reset connection)")
        print(menu_4)
        print(menu_5)
        print(menu_6)
        print("7. Test Account")
        print("8. About")
        print("0. Save & Exit")
        separator_line()
        menu_option=rlib1.get_int('Selection: [0] ')

    #process menu menu_optionion
        if menu_option == 1:
            #setup new account or replace an old one
            config_account()

        elif menu_option == 2:
            #list existing accounts
            action = input('Show account connection keys? Y/N [N]: ').upper()
            if action=='': action='N'
            list_accounts(action[0]=='Y')

        elif menu_option == 3:
            #delete an account
            list_accounts()
            print("0.  None")
            separator_line()
            action = input('(D)elete account, (R)eset connection, or (C)ancel? [C]: ').upper()
            if action in ['D','R']:
                actIndex = rlib1.get_int('Account #: [0] ') - 1
                sitename = AcctArray[actIndex][0]
                acctnum = AcctArray[actIndex][1]
                user=AcctArray[actIndex][3]
                site = Sites.get(sitename, None)
                if site: url = rlib1.FieldVal(site,'url')      #example: url='https://test.ofx.com/my/script'

                if actIndex <= len(AcctArray) and actIndex >= 0 and action=='D':
                    #delete the account
                    log.info('Deleting account %s:%s:%s' % (user, sitename, acctnum))
                    doit = input('Confirm delete (Y/N) ').upper()
                    if doit == 'Y':
                        AcctArray.pop(actIndex)
                        log.info('Account %s:%s:%s deleted.' % (user, sitename, acctnum))

                if site and actIndex >= 0 and action in ['D','R']:
                    #delete clientUID connection key if no other account has the same user/url combo
                    found=False
                    for acct in AcctArray:
                        if acct[0]==sitename and acct[3]==user: found=True
                    if not found:
                        rlib1.clientUID(url, user, delKey=True)
                        if action=='R': log.info('Connection settings reset for %s @ %s' % (user, url))

        elif menu_option == 4:
            #change security settings
            while True:
                pwkey1 = rlib1.getDes_pw('Enter NEW password')
                pwkey2 = rlib1.getDes_pw('ReEnter password')

                if pwkey2 == pwkey1:
                    pwkey = pwkey1
                    break
                else:
                    print('\nPasswords do not match.  Try again...\n')

        elif menu_option == 5:
            #remove security
            if len(pwkey):
                doit = input('Remove file encryption and password protection (Y/N) ').upper()
                if doit == 'Y':
                    pwkey=''

        elif menu_option == 6:
            #enable/disable stock quotes
            c_getquotes = not c_getquotes
            if c_getquotes:
                doit = (input('Do you want to test Quote downloads? (Y/N)? ').upper() == 'Y')
                if doit:
                    test_quotes()

        elif menu_option == 7:
            #test an account
            acctnum = -1

            list_accounts()
            ticker_test = len(AcctArray)+1
            print('{0:4}{1:20}'.format(str(ticker_test)+'.','Stock/Fund Prices'))
            print('0.  None')
            separator_line()
            acctnum = rlib1.get_int('Test account #: [0] ')
            if acctnum <= len(AcctArray) and acctnum != 0:
                acctnum = acctnum-1
                acct = AcctArray[acctnum][0] + ' | ' + AcctArray[acctnum][1]
                #test the account
                doit = input('Test '+ acct+ ' (Y/N)? ').upper()
                if doit == 'Y':
                    test_acct(AcctArray[acctnum])
            elif acctnum == ticker_test:
                doit = input('Test Stock/Fund Pricing Updates (Y/N)? ').upper()
                if doit == 'Y':
                    test_quotes()

        elif menu_option == 8:
            #About
            print("\n\n"+"*"*70+"\n")
            print(AboutTitle)
            print("-"*70)
            print("Retrieve online statements and stock quotes to Microsoft Money")
            print("\tSource :", AboutSource)
            print("\tVersion:", AboutVersion)
            print("\n\n"+"*"*70+"\n")
            input('Press Enter to continue')

    #end_while (main menu)

    if len(pwkey):
        #encrypt the data
        #encrypt the accounts
        rlib1.acctEncrypt(AcctArray,pwkey)
        #encrypt the passkey
        k = pyDes.des(pwkey)
        pwkey = k.encrypt(pwkey, ' ')

    #write the data
    f = open(cfgFile, 'wb')
    pickle.dump(pwkey, f)        #encrypted key (pw)
    pickle.dump(c_getquotes, f)  #get stock quotes?
    pickle.dump(AcctArray, f)    #account info
    f.close()
    log.info('-----------------------------------------------------------------------------------')
