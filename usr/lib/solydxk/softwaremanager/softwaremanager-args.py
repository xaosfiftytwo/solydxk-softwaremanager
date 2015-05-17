#!/usr/bin/env python

# softwaremanager
#    No Copyright (What for?) Clem <root@solydxk.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; Version 2
# of the License.
#
# This program is "inspired" by CNR and the idea of "one click install".

try:
    import pygtk
    pygtk.require("2.0")
except:
    pass
try:
    import sys
    import apt
    import string
    import gtk
    import gtk.glade
    import os
    import functions
    import commands
    import threading
    import tempfile
    import gettext

except Exception, detail:
    print detail
    sys.exit(1)

from subprocess import Popen    #, PIPE

gtk.gdk.threads_init()

# i18n
gettext.install("solydxk-softwaremanager", "/usr/share/locale")

class softwaremanagerExecuter(threading.Thread):

    def __init__(self, window_id, rightRepositories):
        threading.Thread.__init__(self)
        self.window_id = window_id
        self.rightRepositories = rightRepositories

    def execute(self, command):
        #print "Executing: " + command
        os.system(command)
        ret = commands.getoutput("echo $?")
        return ret

    def run(self):
        global steps
        global progressbar
        global wTree
        global packages
        global user
        global home

        wTree.get_widget("main_button").hide()
        wTree.get_widget("cancel_button").set_label("gtk-cancel")
        wTree.get_widget("cancel_button").set_use_stock(True)

        totalSteps = steps
        if (self.rightRepositories != "local"):
            progressbar.set_text(_("Backing up your APT sources"))
            self.execute("mv /etc/apt/sources.list /etc/apt/sources.list.swmbackup")
            self.execute("cp /usr/share/solydxk/softwaremanager/sources.list /etc/apt/sources.list")
            cache = apt.Cache()
            os.system("apt-get update")
            totalSteps = steps + 2

        fraction = 0
        progressbar.set_fraction(fraction)

        for i in range(steps + 1):
            if (i > 0):
                openfile = open("/usr/lib/solydxk/softwaremanager/tmp/steps/"+str(i), 'r' )
                datalist = openfile.readlines()
                for j in range( len( datalist ) ):
                    if (str.find(datalist[j], "TITLE") > -1):
                        title = datalist[j][6:]
                        progressbar.set_text(str.strip(title))
                    if (str.find(datalist[j], "INSTALL") > -1):
                        install = datalist[j][8:]
                        install = str.strip(install)
                        installPackages = string.split(install)
                        cmd = ["sudo", "/usr/sbin/synaptic", "--hide-main-window", "--non-interactive", "--parent-window-id", self.window_id]
                        cmd.append("--progress-str")
                        cmd.append("\"" + _("Please wait, this can take some time") + "\"")
                        cmd.append("--finish-str")
                        cmd.append("\"" + _("Installation is complete") + "\"")
                        f = tempfile.NamedTemporaryFile()
                        for pkg in installPackages:
                            f.write("%s\tinstall\n" % pkg)
                            cmd.append("--set-selections-file")
                            cmd.append("%s" % f.name)
                            f.flush()
                            comnd = Popen(' '.join(cmd), shell=True)
                        returnCode = comnd.wait()
                        f.close()

                    if (str.find(datalist[j], "SOURCE") > -1):
                        source = datalist[j][7:]
                        source = source.rstrip()
                        self.execute("echo \"" + source + "\" >> /etc/apt/sources.list")
                        os.system("apt-get update")
                    if (str.find(datalist[j], "EXECUTE") > -1):
                        execution = datalist[j][8:]
                        execution = execution.rstrip()
                        execution = execution.replace("<<USER>>", user)
                        execution = execution.replace("<<HOME>>", home)
                        self.execute(execution)

                fraction = float(i)/float(totalSteps)
                progressbar.set_fraction(fraction)

        if (self.rightRepositories != "local"):
            progressbar.set_text(_("Restoring your APT sources"))
            self.execute("mv /etc/apt/sources.list.swmbackup /etc/apt/sources.list")
            os.system("apt-get update")
        progressbar.set_fraction(1)
        progressbar.set_text(_("Finished"))
        wTree.get_widget("main_button").hide()
        wTree.get_widget("cancel_button").set_label(_("Close"))
        #Everything is done, exit quietly
        gtk.main_quit()
        sys.exit(0)

class softwaremanagerWindow:
    """This is the main class for the application"""

    def __init__(self, solydxkFile, user, home):
        global steps
        global progressbar
        global wTree
        global installation_terminal
        global installation_progressbar
        global download_progressbar
        global packages

        self.swmFile = solydxkFile
        self.user = user
        self.home = home

        #Make tmp folder
        os.system("mkdir -p /usr/lib/solydxk/softwaremanager/tmp")

        #Clean tmp files
        os.system("rm -rf /usr/lib/solydxk/softwaremanager/tmp/*")

        #Decompress file
        os.system("cp " + solydxkFile + " /usr/lib/solydxk/softwaremanager/tmp/file.swm")
        os.system("tar xf /usr/lib/solydxk/softwaremanager/tmp/file.swm -C /usr/lib/solydxk/softwaremanager/tmp/") #Try without gzip
        os.system("tar zxf /usr/lib/solydxk/softwaremanager/tmp/file.swm -C /usr/lib/solydxk/softwaremanager/tmp/") #Try with gzip

        #Extract the name
        self.name = commands.getoutput("cat /usr/lib/solydxk/softwaremanager/tmp/name")
        self.name = str.strip(self.name)

        #Extract the number of steps
        steps = int(commands.getoutput("ls -l /usr/lib/solydxk/softwaremanager/tmp/steps/ | wc -l"))
        steps = steps -1
        self.pulse = 1/steps

        #Initialize APT
        cache = apt.Cache()

        #Extract repositories and packages
        self.repositories = []
        packages = []
        for i in range(steps + 1):
            if (i > 0):
                openfile = open("/usr/lib/solydxk/softwaremanager/tmp/steps/"+str(i), 'r' )
                datalist = openfile.readlines()
                for j in range( len( datalist ) ):
                    if (str.find(datalist[j], "INSTALL") > -1):
                        install = datalist[j][8:]
                        install = str.strip(install)
                        packages.append(install)
                    if (str.find(datalist[j], "SOURCE") > -1):
                        source = datalist[j][7:]
                        source = source.rstrip()
                        self.repositories.append(source)
                #openfile.close()

        #Set the Glade file
        self.gladefile = "/usr/share/solydxk/softwaremanager/softwaremanager-args.glade"
        wTree = gtk.glade.XML(self.gladefile,"main_window")
        wTree.get_widget("main_window").set_icon_from_file("/usr/share/solydxk/softwaremanager/icon.svg")
        wTree.get_widget("main_window").set_title("")

        wTree.get_widget("main_window").connect("destroy", self.giveUp)

        # Get the window socket (needed for synaptic later on)
        vbox = wTree.get_widget("vbox1")
        socket = gtk.Socket()
        vbox.pack_start(socket)
        socket.show()
        window_id = repr(socket.get_id())

        wTree.get_widget("label_repositories").set_text(_("Using the following repositories:"))

        #Fill in the GUI with information from the solydxkFile
        wTree.get_widget("main_button_label").set_text(_("Install"))

        wTree.get_widget("txt_name").set_text("<big><b>" + _("Install %s?") % (self.name) + "</b></big>")
        wTree.get_widget("txt_name").set_use_markup(True)

        wTree.get_widget("txt_guidance").set_text(_("The following packages will be installed:"))

        if (len(self.repositories) == 0):
            treeview = wTree.get_widget("tree_repositories")
            column1 = gtk.TreeViewColumn()
            renderer = gtk.CellRendererText()
            column1.pack_start(renderer, False)
            column1.set_attributes(renderer, text = 0)
            treeview.append_column(column1)
            treeview.set_headers_visible(False)
            model = gtk.ListStore(str)
            model.append([_("Default repositories")])
            treeview.set_model(model)
            wTree.get_widget("label_repositories").hide()
            wTree.get_widget("scrolledwindow_repositories").hide()

            treeview = wTree.get_widget("tree_packages")
            column1 = gtk.TreeViewColumn()
            renderer = gtk.CellRendererText()
            column1.pack_start(renderer, False)
            column1.set_attributes(renderer, text = 0)
            treeview.append_column(column1)
            treeview.set_headers_visible(False)
            model = gtk.ListStore(str)

            for package in packages:
                strPackage = package
                try:
                    pkg = cache[package]
                    strPackage = str(package) + " [" + pkg.candidateVersion + "]"
                    for dep in pkg.candidateDependencies:
                        for o in dep.or_dependencies:
                            dependency = cache[o.name]
                            if not dependency.is_installed:
                                strDependency = dependency.name + " [" + dependency.candidateVersion + "]"
                                model.append([strDependency])
                except Exception, detail:
                    print detail
                    pass
                model.append([strPackage])
            treeview.set_model(model)
            treeview.show()
        else:
            treeview = wTree.get_widget("tree_repositories")
            column1 = gtk.TreeViewColumn()
            renderer = gtk.CellRendererText()
            column1.pack_start(renderer, False)
            column1.set_attributes(renderer, text = 0)
            treeview.append_column(column1)
            treeview.set_headers_visible(False)
            model = gtk.ListStore(str)
            for repository in self.repositories:
                model.append([repository])
            treeview.set_model(model)
            treeview.show()

            treeview = wTree.get_widget("tree_packages")
            column1 = gtk.TreeViewColumn()
            renderer = gtk.CellRendererText()
            column1.pack_start(renderer, False)
            column1.set_attributes(renderer, text = 0)
            treeview.append_column(column1)
            treeview.set_headers_visible(False)
            model = gtk.ListStore(str)
            for package in packages:
                model.append([package])
            treeview.set_model(model)
            treeview.show()

        self.needToInstallSomething = False
        packageNotFoundLocally = False

        for package in packages:
            try:
                pkg = cache[package]
                if not pkg.is_installed:
                    self.needToInstallSomething = True
            except Exception, details:
                print details
                packageNotFoundLocally = True
                self.needToInstallSomething = True

        if ( not self.needToInstallSomething ):
            #wTree.get_widget("main_window").set_title(_("Upgrade %s?") % (self.name))
            wTree.get_widget("txt_name").set_text("<big><b>" + _("Upgrade %s?") % (self.name) + "</b></big>")
            wTree.get_widget("txt_name").set_use_markup(True)
            wTree.get_widget("txt_guidance").set_text(_("The following packages will be upgraded:"))
            wTree.get_widget("main_button_label").set_text(_("Upgrade"))

        if (len(self.repositories) > 0):
            #The solydxk file defines repositories so we use them.
            rightRepositories = "solydxk"
        else:
            if (packageNotFoundLocally):
            #The solydxk file doesn't define repositories but the package isn't found with the user's repos.. so we use the ones from solydxksystem
                rightRepositories = "default"
            else:
            #The solydxk file doesn't define repositories but the package is found with the user's repos.. so we use the user's repositories (no update required)
                rightRepositories = "local"

        progressbar = wTree.get_widget("progressbar1")
        fraction = 0
        progressbar.set_fraction(fraction)

        download_progressbar = wTree.get_widget("download_progressbar")
        wTree.get_widget("main_window").show()

        #Create our dictionay and connect it
        dic = {"on_main_button_clicked" : (self.MainButtonClicked, window_id, rightRepositories, wTree), "on_cancel_button_clicked" : (self.giveUp) }
        wTree.signal_autoconnect(dic)

    def MainButtonClicked(self, widget, window_id, rightRepositories, wTree):
        wTree.get_widget("main_window").window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        wTree.get_widget("main_window").set_sensitive(False)
        executer = softwaremanagerExecuter(window_id, rightRepositories)
        executer.start()
        return True

    def giveUp(self, widget):
        if (os.path.exists("/etc/apt/sources.list.swmbackup")):
            os.system("mv /etc/apt/sources.list.swmbackup /etc/apt/sources.list")
        gtk.main_quit
        sys.exit(0)

class MessageDialog:
    def __init__(self, title, message):
        self.title = title
        self.message = message

    def show(self):
        warnDlg = gtk.Dialog(title=_("Software Manager"), parent=None, flags=0, buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK))
        warnDlg.vbox.set_spacing(10)
        labelSpc = gtk.Label(" ")
        warnDlg.vbox.pack_start(labelSpc)
        labelSpc.show()
        warnText = ("<b>" + self.title + "</b>")
        infoText = (self.message)
        label = gtk.Label(warnText)
        lblInfo = gtk.Label(infoText)
        label.set_use_markup(True)
        lblInfo.set_use_markup(True)
        warnDlg.vbox.pack_start(label)
        warnDlg.vbox.pack_start(lblInfo)
        label.show()
        lblInfo.show()
        response = warnDlg.run()
        if response == gtk.RESPONSE_OK :
            warnDlg.destroy()

def search_solydxk(widget, username, textfield):
    search_txt = textfield.get_text()
    search_txt = search_txt.replace(" ", "_")
    releaseID = commands.getoutput("cat /usr/share/solydxk/softwaremanager/release.id")
    show_website(username, "http://www.solydxk.com/software/?sec=search&search=" + search_txt + "&release=" + str.strip(releaseID))

def show_portal_solydxk(widget, username):
    releaseID = commands.getoutput("cat /usr/share/solydxk/softwaremanager/release.id")
    show_website(username, "http://solydxk.com/software/?sec=categories&release=" + str.strip(releaseID))

def search_getdeb(widget, username, textfield):
    search_txt = textfield.get_text()
    search_txt = search_txt.replace(" ", "_")
    show_website(username, "http://www.getdeb.net/search.php?keywords=" + search_txt)

def show_portal_getdeb(widget, username):
    show_website(username, "http://www.getdeb.net/")

def show_portal_ubuntu_apt(widget, username):
    show_website(username, "http://packages.ubuntu.com/")

def show_portal_solydxk_apt(widget, username):
    show_website(username, "http://home.solydxk.com/")

def show_website(username, link):
    functions.showWebsite(username, link)

def search_apt(widget, textfield):
    os.system("/usr/lib/solydxk/softwaremanager/search-apt " + textfield.get_text() + " &")

def show_apt(widget, textfield):
    os.system("/usr/lib/solydxk/softwaremanager/show-apt " + textfield.get_text() + " &")

def install_apt(widget, textfield, window_id):
    os.system("/usr/lib/solydxk/softwaremanager/make-cmd " + textfield.get_text())

def updateEntries(widget, wTree):
    wTree.get_widget("txt_search_solydxk").set_text(widget.get_text())
    wTree.get_widget("txt_search_getdeb").set_text(widget.get_text())
    wTree.get_widget("txt_apt").set_text(widget.get_text())

global user
global home
if __name__ == "__main__":
    if (len(sys.argv) != 4):
        username = sys.argv[1]
        gladefile = "/usr/share/solydxk/softwaremanager/softwaremanager-args.glade"
        wTree = gtk.glade.XML(gladefile,"window_menu")

        # Get the window socket (needed for synaptic later on)
        vbox = wTree.get_widget("vbox3")
        socket = gtk.Socket()
        vbox.pack_start(socket)
        socket.show()
        window_id = repr(socket.get_id())

        wTree.get_widget("window_menu").connect("destroy", gtk.main_quit)
        wTree.get_widget("button_portal_solydxk").connect("clicked", show_portal_solydxk, username)
        wTree.get_widget("button_search_solydxk").connect("clicked", search_solydxk, username, wTree.get_widget("txt_search_solydxk"))
        wTree.get_widget("txt_search_solydxk").connect("activate", search_solydxk, username, wTree.get_widget("txt_search_solydxk"))
        wTree.get_widget("button_portal_getdeb").connect("clicked", show_portal_getdeb, username)
        wTree.get_widget("button_search_getdeb").connect("clicked", search_getdeb, username, wTree.get_widget("txt_search_getdeb"))
        wTree.get_widget("txt_search_getdeb").connect("activate", search_getdeb, username, wTree.get_widget("txt_search_getdeb"))
        wTree.get_widget("button_portal_ubuntu_apt").connect("clicked", show_portal_ubuntu_apt, username)
        wTree.get_widget("button_portal_solydxk_apt").connect("clicked", show_portal_solydxk_apt, username)
        wTree.get_widget("button_search_apt").connect("clicked", search_apt, wTree.get_widget("txt_apt"))
        wTree.get_widget("button_install_apt").connect("clicked", install_apt, wTree.get_widget("txt_apt"), window_id)
        wTree.get_widget("button_show_apt").connect("clicked", show_apt, wTree.get_widget("txt_apt"))
        wTree.get_widget("txt_search_solydxk").connect("changed", updateEntries, wTree)
        wTree.get_widget("txt_search_getdeb").connect("changed", updateEntries, wTree)
        wTree.get_widget("txt_apt").connect("changed", updateEntries, wTree)
        wTree.get_widget("window_menu").set_icon_from_file("/usr/share/solydxk/softwaremanager/icon.svg")
        wTree.get_widget("window_menu").set_title(_("Find Software"))

        #i18n
        wTree.get_widget("button_portal_solydxk_label").set_label(_("Go to the SolydXK Software Portal"))
        wTree.get_widget("button_search_solydxk_label").set_label(_("Search for a .swm application"))
        wTree.get_widget("button_portal_getdeb_label").set_label(_("Go to the GetDeb Portal"))
        wTree.get_widget("button_search_getdeb_label").set_label(_("Search for a .deb package"))
        wTree.get_widget("button_search_apt_label").set_label(_("Search"))
        wTree.get_widget("button_install_apt_label").set_label(_("Install"))
        wTree.get_widget("button_show_apt_label").set_label(_("Show"))
        wTree.get_widget("button_portal_ubuntu_apt_label").set_label(_("Go to the Ubuntu repository"))
        wTree.get_widget("button_portal_solydxk_apt_label").set_label(_("Go to the SolydXK repository"))
        wTree.get_widget("txt_search_solydxk").grab_focus()
        wTree.get_widget("window_menu").show()
        gtk.gdk.threads_enter()
        gtk.main()
        gtk.gdk.threads_leave()
    else:
        os.system("rm -rf /var/lib/dpkg/lock")
        os.system("rm -rf /var/lib/apt/lists/lock")
        os.system("rm -rf /var/cache/apt/archives/lock")

        if (os.path.exists("/etc/apt/sources.list.swmbackup")):
            os.system("mv /etc/apt/sources.list.swmbackup /etc/apt/sources.list")
            os.system("sudo apt-get update")
            message = MessageDialog(_("Your APT sources were corrupted."), _("Your APT sources were not correctly restored after you last ran softwaremanager. They now have been restored."))
            message.show()
            sys.exit(0)
        else:
            username = sys.argv[2]
            home = sys.argv[3]
            mainwin = softwaremanagerWindow(sys.argv[1], username, home)
            gtk.gdk.threads_enter()
            gtk.main()
            gtk.gdk.threads_leave()
