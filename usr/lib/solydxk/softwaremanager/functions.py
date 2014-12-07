#!/usr/bin/env python -u

import os
import webbrowser
import apt


def showWebsite(username, link):
    wb = webbrowser.get()
    os.system("sudo -u " + username + " " + wb.name + " \"" + link + "\"")


# Get the package version number
def getPackageVersion(packageName, candidate=False):
    version = ''
    try:
        cache = apt.Cache()
        pkg = cache[packageName]
        if candidate:
            version = pkg.candidate.version
        elif pkg.installed is not None:
            version = pkg.installed.version
    except:
        pass
    return version
