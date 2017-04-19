import json
from burp import IBurpExtender
from burp import IExtensionStateListener
from burp import IContextMenuFactory
from burp import IContextMenuInvocation
from burp import ITab
from java.awt import EventQueue
from java.awt.event import ActionListener
from java.awt.event import ItemListener
from java.lang import Runnable
from javax.swing import JCheckBox
from javax.swing import JMenu
from javax.swing import JMenuBar
from javax.swing import JMenuItem
from javax.swing import JLabel
from javax.swing import JPanel
from javax.swing import JSplitPane
from javax.swing import JScrollPane
from javax.swing import JTabbedPane
from javax.swing import JTextArea
from javax.swing import JTree
from javax.swing.event import TreeSelectionEvent
from javax.swing.event import TreeSelectionListener
from javax.swing.tree import DefaultMutableTreeNode
from javax.swing.tree import TreeSelectionModel

# Using the Runnable class for thread-safety with Swing
class Run(Runnable):
    def __init__(self, runner):
        self.runner = runner

    def run(self):
        self.runner()

# TODO: Refactor to move functions into their own classes based on
#       functionality
class BurpExtender(IBurpExtender, IExtensionStateListener, IContextMenuFactory, ITab):
    EXTENSION_NAME = "Bug Catcher"

    def __init__(self):
        data = Data()

        self.checklist = data.get_checklist()
        self.issues = data.get_issues()
        self.checklist_tree = self.create_checklist_tree()
        self.tree = self.create_tree()
        self.pane = self.create_pane()
        self.tabbed_panes = self.create_tabbed_panes()
        self.create_tsl()

    def registerExtenderCallbacks(self, callbacks):
        self.callbacks = callbacks
        self.helpers = callbacks.getHelpers()
        self.callbacks.registerExtensionStateListener(self)
        self.callbacks.setExtensionName(self.EXTENSION_NAME)
        self.callbacks.addSuiteTab(self)
        self.callbacks.registerContextMenuFactory(self)

    def createMenuItems(self, invocation):
        # Do not create a menu item unless getting a context menu from the proxy history
        is_proxy_history = invocation.getInvocationContext() == invocation.CONTEXT_PROXY_HISTORY

        if not is_proxy_history:
            return

        functionality = self.checklist["functionality"]

        # Create the menu item for the Burp context menu
        bugcatcher_menu = JMenu("Send to Bug Catcher")

        # TODO: Sort the functionality by name and by vuln class
        for functionality_name in functionality:
            vulns = functionality[functionality_name]["vulns"]
            menu_vuln = JMenu(functionality_name)

            # Create a menu item and an action listener per vulnerability
            # class on each functionality
            for vuln_name in vulns:
                item_vuln = JMenuItem(vuln_name)
                item_vuln.addActionListener(MenuItem(self.tree, self.pane, functionality_name, vuln_name, self.tabbed_panes))
                menu_vuln.add(item_vuln)

            bugcatcher_menu.add(menu_vuln)

        burp_menu = []
        burp_menu.append(bugcatcher_menu)

        return burp_menu

    def getTabCaption(self):
        return self.EXTENSION_NAME

    def getUiComponent(self):
        return self.pane

    def extensionUnloaded(self):
        print "Bug Catcher plugin unloaded"
        return

    # TODO: Move to View class
    # TODO: Use Bugcrowd API to grab the Program Brief and Targets
    # Creates a DefaultMutableTreeNode using the JSON file data
    def create_checklist_tree(self):
        functionality = self.checklist["functionality"]

        root = DefaultMutableTreeNode("Bug Catcher Check List")
        root.add(DefaultMutableTreeNode("Settings"))
        root.add(DefaultMutableTreeNode("Program Brief"))
        root.add(DefaultMutableTreeNode("Targets"))

        # TODO: Sort the functionality by name and by vuln class
        for functionality_name in functionality:
            vulns = functionality[functionality_name]["vulns"]
            node = DefaultMutableTreeNode(functionality_name)

            for vuln_name in vulns:
                node.add(DefaultMutableTreeNode(vuln_name))

            root.add(node)

        return root

    # Creates a JTree object from the checklist
    def create_tree(self):
        tree = JTree(self.checklist_tree)
        tree.getSelectionModel().setSelectionMode(
            TreeSelectionModel.SINGLE_TREE_SELECTION
        )

        return tree

    # TODO: Move to View class
    # TODO: Figure out how to use JCheckboxTree instead of a simple JTree
    # TODO: Change to briefcase icon for brief, P1-P5 icons for vulns,
    #       bullseye icon for Targets, etc
    # Create a JSplitPlane with a JTree to the left and JTabbedPane to right
    def create_pane(self):
        status = JTextArea()
        status.setLineWrap(True)
        status.setText("Nothing selected")
        self.status = status

        pane = JSplitPane(JSplitPane.HORIZONTAL_SPLIT,
                JScrollPane(self.tree),
                JTabbedPane()
        )

        return pane

    def create_tsl(self):
        tsl = TSL(self.tree, self.pane, self.checklist, self.issues, self.tabbed_panes)
        self.tree.addTreeSelectionListener(tsl)

        return

    # Creates the tabs dynamically using data from the JSON file
    def create_tabbed_panes(self):
        functionality = self.checklist["functionality"]
        tabbed_panes = {}

        for functionality_name in functionality:
            vulns = functionality[functionality_name]["vulns"]

            for vuln_name in vulns:
                key = functionality_name + "." + vuln_name
                tabbed_pane = self.create_tabbed_pane(functionality_name, vuln_name)
                tabbed_panes[key] = tabbed_pane

        return tabbed_panes

    # Creates a JTabbedPane for each vulnerability per functionality
    def create_tabbed_pane(self, functionality_name, vuln_name):
        description_tab = self.create_description_tab(functionality_name, vuln_name)
        bugs_tab = self.create_bugs_tab()
        resources_tab = self.create_resource_tab(functionality_name, vuln_name)
        notes_tab = self.create_notes_tab()

        tabbed_pane = JTabbedPane()
        tabbed_pane.add("Description", description_tab)
        tabbed_pane.add("Bugs", bugs_tab)
        tabbed_pane.add("Resources", resources_tab)
        tabbed_pane.add("Notes", notes_tab)

        return tabbed_pane

    # Creates the description panel
    def create_description_tab(self, fn, vn):
        description_text = str(self.checklist["functionality"][fn]["vulns"][vn]["description"])
        description_textarea = JTextArea()
        description_textarea.setLineWrap(True)
        description_textarea.setText(description_text)
        description_panel = JScrollPane(description_textarea)

        return description_panel

    # TODO: Add functionality to remove tabs
    # Creates the bugs panel
    def create_bugs_tab(self):
        bugs_tab = JTabbedPane()

        return bugs_tab

    # Creates the resources panel
    def create_resource_tab(self, fn, vn):
        resource_urls = self.checklist["functionality"][fn]["vulns"][vn]["resources"]
        resource_text = ""

        for url in resource_urls:
            resource_text = resource_text + str(url) + "\n"

        resource_textarea = JTextArea()
        resource_textarea.setLineWrap(True)
        resource_textarea.setWrapStyleWord(True)
        resource_textarea.setText(resource_text)
        resources_panel = JScrollPane(resource_textarea)

        return resources_panel

    def create_notes_tab(self):
        notes_textarea = JTextArea()

        return notes_textarea

class MenuItem(ActionListener):
    def __init__(self, tree, pane, functionality_name, vuln_name, tabbed_panes):
        self.tree = tree
        self.pane = pane
        self.key = functionality_name + "." + vuln_name
        self.tabbed_panes = tabbed_panes

    def actionPerformed(self, e):
        bugs_tab = self.tabbed_panes[self.key].getComponentAt(1)
        tab_count = str(bugs_tab.getTabCount())
        bugs_tab.add(tab_count, JScrollPane())

# ItemListener that will write back to the issues.json file whenever something on the
# settings is checked or unchecked
class Settings(ItemListener):
    def __init__(self, issues, vuln_names, vuln_name, is_enabled):
        self.issues = issues
        self.vuln_names = vuln_names
        self.vuln_name = vuln_name
        self.is_enabled = is_enabled

    def itemStateChanged(self, e):
        is_checked = int(e.getStateChange()) == 1
        is_unchecked = int(e.getStateChange()) == 2

        if is_checked:
            self.issues["issues"][self.vuln_name]["enabled"] = True
            print self.vuln_name + " was checked"

        if is_unchecked:
            self.issues["issues"][self.vuln_name]["enabled"] = False
            print self.vuln_name + " was unchecked"

        with open("issues.json", "w") as data:
            data.write(json.dumps(self.issues, indent=2, sort_keys=True))
            data.close()

# TODO: Put function for getting data here
class Data():
    shared_state = {}

    def __init__(self):
        self.__dict__ = self.shared_state
        self.set_checklist()
        self.set_issues()

    def set_checklist(self):
        with open("checklist.json") as data_file:
            data = json.load(data_file)
            self.checklist = data["checklist"]

    def get_checklist(self):
        return self.checklist

    def set_issues(self):
        with open("issues.json") as data_file:
            self.issues = json.load(data_file)

    def get_issues(self):
        return self.issues

# TODO: Put all functions pertaining to creating the Burp views
class View():
    def __init__(self):
        return

class TSL(TreeSelectionListener):
    def __init__(self, tree, pane, checklist, issues, tabbed_panes):
        self.tree = tree
        self.pane = pane
        self.checklist = checklist
        self.issues = issues
        self.tabbed_panes = tabbed_panes

    def valueChanged(self, tse):
        pane = self.pane
        node = self.tree.getLastSelectedPathComponent()

        vuln_name = node.toString()
        functionality_name = node.getParent().toString()

        # TODO: Move Program Brief and Targets nodes creation elsewhere
        is_leaf = node.isLeaf()
        is_settings = is_leaf and (vuln_name == "Settings")
        is_brief = is_leaf and (vuln_name == "Program Brief")
        is_target = is_leaf and (vuln_name == "Targets")
        is_functionality = is_leaf and not (is_settings or is_brief or is_target)

        if node:
            if is_functionality:
                key = functionality_name + "." + vuln_name
                tabbed_pane = self.tabbed_panes[key]
                pane.setRightComponent(tabbed_pane)
            elif is_settings:
                settings_pane = self.create_settings_pane()
                pane.setRightComponent(settings_pane)
            elif is_brief:
                brief_textarea = JTextArea()
                brief_textarea.setLineWrap(True)
                brief_textarea.setText("This is the program brief:")

                pane.setRightComponent(brief_textarea)
            elif is_target:
                target_textarea = JTextArea()
                target_textarea.setLineWrap(True)
                target_textarea.setText("These are the targets:")

                pane.setRightComponent(target_textarea)
            else:
                name = node.toString()
                functionality_textarea = JTextArea()
                functionality_textarea.setLineWrap(True)
                functionality_textarea.setText("Make a description for: " + name)

                pane.setRightComponent(functionality_textarea)
        else:
            pane.setRightComponent(JLabel('I AM ERROR'))

    def create_settings_pane(self):
        pane = JPanel()

        issues = self.issues
        vuln_names = issues["issues"]

        for vuln_name in vuln_names:
            is_enabled = vuln_names[vuln_name]["enabled"]
            enabled_checkbox = JCheckBox(vuln_name, is_enabled)
            enabled_checkbox.addItemListener(Settings(issues, vuln_names, vuln_name, is_enabled))
            pane.add(enabled_checkbox)

        return pane


if __name__ in [ '__main__', 'main' ] :
    EventQueue.invokeLater(Run(BurpExtender))
