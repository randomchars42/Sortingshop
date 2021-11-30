# SortingShop

... to sort your 1,000,000 photos, taken to be marveled at again.

The aim is to make tagging and sorting as fast and efficient as possible. [No need to take your hands of the keyboard](#how)!

## What happens

1. You choose a directory containing photos.
2. You may press "Prepare mediafiles" and **whoosh**:
  * All files may\* be renamed following a certain pattern.
  * For each file a sidecar ([What's that?](#sidecars)) may\* be created.
  * A set of tags may\* be added.
  * Certain metadata may\* be removed.
3. You may press "Start tagging files" and you'll be shown each file in turn so you can add or remove tags and ratings or mark the file for removal\*\*.

   While you work your way through your collection every file you encounter may be renamed, have a sidecar created, tags added and metadata removed\*.

4. When you're finished you may hit "Sort mediafiles by tags" and your files will be sorted by a tag\*\*\* you have added.

\*) What happens to your files may be configured. Be sure to check the configuration and test it on some duplicate files to be sure nothing's lost once you start on your collection.
\*\*) Files are, by concept, not removed but rather moved to a directory named "deleted" so you can have second thoughts.
\*\*\*) Which tag, again, can be specified in the configuration. I apply a tag describing the event to each picture and let the programme sort the images accordingly.

## Why?

Chances are you probably take far too many pictures to ever find your favourites again. You could for a start click on each image and afterwards drag'n'drop it into a folder on your computer. Or, if you don't like the picture, just delete it. Chances are you'll end up with a useable collection.

But what if you would like to find all pictures of your favourite pet?

Thats were metadata comes into play.

### Metadata

Metadata are small bits of information stored in the pictures themselves. By the time you take a picture a lot of information is stored alongside it, like the date and time, the camera model, and much more.

What information gets stored greatly depends on the manufacturer of your phone / app / camera.

### Tags

In addition to technical information you may add some information like "Christmas 2021", "Holidays in France" or "John Doe". Those bits of information will help you to find the picture later on.

### Sidecars

Sidecars are text files stored alongside your pictures. They can contain tags and much more. Photo editing programmes like [Darktable](https://darktable.org) or *Adobe Photoshop* can use sidecars to store processing steps. In theory you can have multiple sidecars per picture - one containing the steps to enhance the contrast and colours, one converting it to that nice sepia-toned monochromatic image.

If you choose to, `SortingShop` will copy some information into a sidecar and from then on use the sidecar to store tags. Why? You could "lock" your picture so no further programme can write to it and add its own bit of gibberish / information and thereby risking to mess up your collection - or worse, destroy the image.

## How?

### Tagging

Once you've started `SortingShop` and hit "Start tagging files" you will see a couple of things.

To the left there's the first picture.

In the next column you can topmost choose where to store the metadata (but if you've configured `SortingShop` to your liking you most likely won't have to).

Below, you see an input field - that's where you will work most of the time - **your hands will stay on the keyboard, no need to chase after your mouse!**. Here you can enter [commands](#commands) for tagging, rating, deleting, undeleting, rotating, flipping [and much more](#commands).

Even further down you'll see the tags which are currently stored in the sidecar / picture.

The next column to the right holds ["tagsets" - abbreviations so you can add / remove multiple tags with a few keystrokes](#tagsets).

The right-most columns shows metadata appart from tags.

#### Commands

* `t TAG1,TAG2,TAG3,ABBR1,...`: **t**oggle (add if not there, or else remove) TAG1, TAG2, TAG3, [all tags contained in ABBR1](#tagsets), ...
* `.`: toggle the last tags again (to remove them or to use them in the next image)
* `n`: go to the **n**ext image
* `p`: go to the **p**revious image
* `H`: display the **h**elp
* `0`, `1`, `2`, ..., `5`: apply a 0, 1, 2, ..., 5 star rating
* `r`: mark the picture as **r**ejected
* `d`: **d**elete the picture
* `: NUMBER`: jump to picture no. NUMBER
* `: NAME`: jump to the picture named NAME
* `c`: rotate the image 90 ° **c**lockwise
* `C`: rotate the image 90 ° **C**ounterclockwise
* `h`: flip the image **h**orizontically
* `v`: flip the image **v**orizontically
* `N`: switch to **N**ext metadata source (image, sidecar 1, sidecar 2, ...)
* `P`: switch to **P**revious metadata source (image, sidecar 1, sidecar 2, ...)

#### Tagsets

Tagsets let you toggle multiple tags with a few keystrokes.

They can be stored in two text files:
* One is in your configuration, `~/.config/sortingshop/tagsets` that is. This one is called *global*, it will be loaded no matter which folder of pictures you are working on.
* The other one would also be called `tagsets` and would be in the folder you are working in. This one would be called *local* as it is local to the folder you are currently working on.

Tagsets are stored one per line: first comes the abbreviation you will type to toggle the tags, then follows a blank (` `) and next the tags you will toggle with the abbreviation.

The following file will define two abbreviations. The first one (*"hol"*) will toggle the tags: `Location|Nice Place`, `Event|Holiday 2021`, the second one (*"we"*) will toggle: `Person|John Doe`, `Person|Jane Doe` and `Person|Little Tom Doe`.

```
hol Location|Nice Place,Event|Holiday 2021
we Person|John Doe,Person|Jane Doe,Person|Little Tom Doe
```

*Local* tagsets take precedence over *global* tagsets. So if above tags were defined *globally* but you're working on the pictures of the holiday when Granny was with you, you might create a *local* tagsets file like:

```
we Person|John Doe,Person|Jane Doe,Person|Little Tom Doe,Person|Granny
```

So, *"we"* will now toggle: `Person|John Doe`, `Person|Jane Doe`, `Person|Little Tom Doe` and `Person|Granny`.

There's a special tagset called `ALL_PICTURES`. Those tags will be applied to the images automatically.

### Configuration

The [configuration](../master/src/sortingshop/settings/config.ini) looks like this:

```ini
[Paths]
; if you want to start with the same directory every time enter it here
working_dir =
; your global tagsets reside here
path_tagsets = ~/.config/sortingshop/tagsets

[UI]
; maximal dimension of the displayed image in px
image_max_size = 600
; the height of the metadata field in px
metadata_field_size_vertical = 300

[Renaming]
rename_files = true
; must be compatible with exiftool
; see https://exiftool.org/filename.html
rename_command = -d IMG_%Y-%m-%d_%H-%M-%S%%+.3nc.%%le -filename<FileModifyDate -filename<ModifyDate -filename<CreateDate -filename<DateTimeOriginal -v
; regex for python to detect if a file is named appropriatly
; all variables supported by strftime may be used, special fields like %%c or
; %%e that are not recognised by strftime should be marked as a variable (.)
; for example in the rename scheme above
;  - %%+.3nc results in a three-digit counter preceded by "_": "_XXX" (see counter_length and mediafile_name_has_counter)
;  - %%le results in a lower-case extension
detect_scheme = IMG_%Y-%m-%d_%H-%M-%S_.{3}\.[a-z]+
; in case of duplicate filenames a counter is placed before the extension
; e.g., IMG_2021-01-01_00-00-01.jpg exists, and another file that would be renamed to have the same name
; would become IMG_2021-01-01_00-00-01_001.jpg
; this option sets the number of digits of that counter
counter_length = 3
; the default naming scheme above already has a counter incorporated in its naming rule
mediafile_name_has_counter = true

[Metadata]
; field to store tags:
field_tags = HierarchicalSubject
; automatically create a sidecar MEDIAFILE.EXTENSION.xmp and write to sidecar instead
use_sidecar = true
; assume a file is prepared if
; - it has a sidecar if it needs one (use_sidecar) and
; - it is named correctly (detect_scheme) if it needs to (rename_files)
; else do renaming nonetheless and attempt to create a sidecar
soft_check = true
; remove unwanted tags from the mediafile, especially when creating sidecars so theres little chance of discrepancy between the two
prune_metadata = true
; when pruning (see above) write the following tags to file / sidecar
; see https://exiftool.org/TagNames/index.html for an overview of the tags (whitespace delimited)
mandatory_metadata = lr:hierarchicalSubjects xmp:Rating DateTimeOriginal
; prune (see above) the following tags (whitespace delimited)
remove_metadata = IPTC XMP IFD0:Copyright IFD0:Artist IFD0:ProcessingSoftware IFD0:Software IFD0:Rating IFD0:RatingPercent ExifIFD:UserComment File:Comment IFD0:ImageDescription
; apply a default tagset by default
apply_default_tagset = false

[Sorting]
; tags are used for sorting
; the regex should match the part of the tag to sort by and is used in re.sub()
; the following regex catches a part of a tag that is formatted like:
; TAG1|YYYY DESCRIPTION
;      ^^^^^^^^^^^^^^^^
; e.g.
; TAG1|2020 My Greatest Pictures
;      ^^^^^^^^^^^^^^^^^^^^^^^^^
sorting_tag_regex = .*([0-9]{4} [^\/\\]+).*
; replace the tag with only the matched part
; e.g.
; TAG1|2020 My Greatest Pictures
;      ^^^^^^^^^^^^^^^^^^^^^^^^^
; becomes:
; 2020 My Greatest Pictures
; ^^^^^^^^^^^^^^^^^^^^^^^^^
; and is used for sorting
sorting_tag_sub = \g<1>
```

Be sure to tweak it to your liking and store it in `~/.config/sortingshop/config.ini`.

### Give me more technicalities

`SortingShop` uses `xmp.lr.hierarchicalSubjects` to store the tags (a format introduced by *Adobe Lightroom*). As their name implies, those tags are hierarchical meaning if a picture is tagged `Event|Holiday 2021|Trip to Very Nice Place` the picture could be found under `Event`, `Holiday 2021` and `Trip to Very Nice Place`.

`SortingShop` does not access the metadata itself - no need to re-invent the wheel, especially if its a precious wheel like the picture of **THAT** smile of your child. Instead, it uses the excellent and battle-tested [ExifTool](https://www.exiftool.org) by Phil Harvey. Kudos!

## Installation

At the moment there's no way to "install" `SortingShop` (distribution via pip / pipx is underway). You need to download the files and run the programme, e.g. like:

```
$ cd /path/to/code/SortingShop/src
$ python3 -m sortingshop.sortingshop
```

Or create an alias in your `.bash_aliases` to make life easier:

```
alias sortingshop="PYTHONPATH=$PYTHONPATH:/path/to/code/SortingShop/src python3 -m sortingshop.sortingshop -d "'"$(pwd)"'
```

**And don't forget** to replace `/path/to/code`!

You'll need to have [ExifTool](https://www.exiftool.org) and [wxPython](https://pypi.org/project/wxPython/) > 4.0.1 installed. And, of course, Python > 3.6.
