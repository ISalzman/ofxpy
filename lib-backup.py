# functions no longer used

from Cookie import SimpleCookie

def getCookie(respCookie):
    #extract valid request cookie from server-provided cookie string
    #server response may include attributes, but we don't want those in requests
    #cparts  = ''
    #cookies = ''
    #attrib = ['Secure', 'HttpOnly', 'Domain', 'Path', 'Expires', 'SameSite', '__Host']
    #if respCookie != '': cparts = respCookie.split(';')
    #we only want cookies... strip out the attributes 
    #for c in cparts:
    #    if not any(a in c for a in attrib):  #this one doesn't contain a 
    #        if cookies != '': cookies += '; '
    #        cookies += c
    cStr = ''
    if respCookie != '':
        sc = SimpleCookie()
        sc.load(respCookie)
        #below returns a concatenated string of key=value pairs, separated by ;
        cStr = '; '.join('{}={}'.format(key, value.value) for key, value in sc.items())
        if Debug: print('getCookie() result = ', cStr)
    return cStr
