# Summary of the “PersonGN” Gramplet Addon for Gramps
PersonGN is a Gramplet addon plugin for the Person category of the Gramps genealogy software. It enables users to interact with the Geneanet collaboration platform (since 1996, an Ancestry.com like site offering freemium genealogy tree sharing) directly from within Gramps.

It provides the selective Geneanet import and update of a selected person and their immediate relatives.

## For Gramps 6.0:
Add the path for the Jean Michault’s experimental project on GitHub to enable installation via the [Addon Manager](https://gramps-project.org/wiki/index.php/Gramps_Glossary#addon "Link to Gramps wiki").  
```https://raw.githubusercontent.com/jmichault/gramps-kromprogramoj/gramps60```
Then search for PersonGN or Geneanet in the Addons tab.

## For Gramps 5.2:
Try to use [Addon Manager](https://gramps-project.org/wiki/index.php/Gramps_Glossary#addon "Link to Gramps wiki") like with Gramps 6.0. If it doesn't work, download the PersonGN.addon.tgz archive file and install the expanded PersonGN folder to the gramps52/plugins folder.  
<https://github.com/jmichault/gramps-kromprogramoj/tree/gramps60/download>

# Main Features
* Geneanet Integration: PersonGN allows users to search for, compare, and import genealogical data about individuals from Geneanet into their Gramps family tree database.
* Graphical User Interface: The addon creates a GTK-based graphical interface, loading its layout from a Glade file. It provides controls for searching, selecting, and importing data.
* Dependency Management: At startup, the addon checks for required Python dependencies (lxml, protobuf) and provides user guidance if they are missing.
* Data Comparison: The plugin fetches data from Geneanet and compares it with the selected Gramps person, displaying differences in a detailed, interactive table. Users can review facts, relationships, and other attributes side-by-side.
* Selective Data Import: Users can select which Geneanet facts, relationships (parents, spouses, children), or events to import into or update in Gramps. The interface allows toggling which lines to import. A Preferences selection allows excluding Notes.
* Family Relationship Handling: The addon supports importing and updating complex family relationships, such as adding or updating parents, spouses, children, and associated events (like marriage).
* Event and Note Import: It can import or update events (e.g., birth, death, marriage) and notes from Geneanet records into Gramps, ensuring data consistency and avoiding duplicates.
* Language: The Esperanto addon interface has been translated into French, English, Hebrew, Dutch, Brazilian Portuguese.
* Progress Feedback: During data fetching, the plugin displays the number of potential matching individuals being scanned, provides progress feedback, and allows cancellation.
# Technical Details
* Uses Gramps API: The addon makes extensive use of Gramps’ internal APIs for database transactions, person and family management, and event handling.
* Modular Structure: The code is modular, relying on helper modules (e.g., komparoGN, ImportoGN, utilaGN) for comparison, import logic, and utility functions.
* Error Handling: The plugin checks for active windows and handles exceptions to avoid conflicts during editing.
* Open Source: Licensed under GPL 3.0.

# Typical Workflow
* Add the “Geneanet” gramplet to the bottombar or a Person category view.
* Select a person
* Click the “Search” button
* PersonGN fetches potential matching data from Geneanet into a proxy tree.
* The potential matches are displayed as a comparison table of facts and relationships.
* Select the Person to import for review.
* Click the “View on Geneanet” link to review the data in a browser;
* or, click the To Compare button to review the data in the Gramplet.
* Each row is color coded to indicate the synchronization status:
  * white: there is data in gramps, but no matches found.
  * yellow (drop-down lines only): there is additional or discrepant data, drop down the list to see details.
  * green: everything matches
  * orange: this data has no matches in gramps.
  * rouge : there is conflict.
* Select checkboxes for the rows of data to be imported
* clic “Import selection” button, or “Copy a choice from geneanet to gramps” from the right-click context menu.
* Data is copied into Gramps, updating the family tree as needed.

# Purpose
PersonGN streamlines the process of synchronizing and enriching genealogical data in Gramps from Geneanet, reducing manual data entry and ensuring data accuracy and completeness.


