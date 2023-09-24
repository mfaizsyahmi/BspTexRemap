from .types.wad import WadHeader, WadDirEntry, WadMipTex, BadWadFile
from dataclasses import dataclass, field, astuple
from PIL import Image

@dataclass
class WadFile:
    ''' WadFile class for wad3 file.

        This implementation supports loading only the entries for quick skimming.
        In this mode new images can still be added and existing entries can be
        renamed. Only new images will be written, at the end of the untouched
        wad of data. If existing entries are removed, their miptex data will
        remain on the file.

        miptexes list is ABSENT in this implementation. Please use
        self.entries[n]._miptex to get the miptex data associated with the entry.
    '''
    header: WadHeader = field(default_factory=WadHeader)
    entries: list[WadDirEntry] = field(default_factory=list)
    _only_entries: bool        = False
    # miptexes: list[WadMipTex] = field(default_factory=list)

    @classmethod
    def load(cls, fp, only_entries=False):
        ''' if only_entries load just the entries (for quick skimming through)
        '''
        fp.seek(0)
        header = WadHeader.load(fp)

        fp.seek(header.dir_offset)
        size, count = WadDirEntry.STRUCT.size, header.entries
        dir_raw = fp.read(size * count) # read once
        entries = [WadDirEntry.decode(dir_raw[n*size:n*size+size]) \
                   for n in range(count)]

        # miptexes = []
        for item in entries:
            if only_entries:
                item._no_data = True
                continue
            fp.seek(item.offset)
            this_miptex = WadMipTex.load(fp,item.sizeondisk)
            # miptexes.append(this_miptex)
            entries._miptex = this_miptex # reference to the data it's representing

        return cls(header,entries,only_entries) # ,miptexes)

    def dump(self, fp):
        """ lays out the file in this order: (header, miptex, entries)

            if only_entries was True during load, only dump miptexes at the end
            of the existing wad of data, whose entries were added later
        """
        entries_to_dump = filter(lambda x: not x._no_data, self.entries)
        if self._only_entries and header.dir_offset == header.STRUCT.size:
            ''' if direntry happen to come after the header in this mode,
                skip to the very end (this will leave dead data at the start)
            '''
            fp.seek(0,2)
            texdump_offset = fp.tell()
        elif self._only_entries:
            texdump_offset = header.dir_offset
        else:
            texdump_offset = WadHeader.STRUCT.size

        self.header.entries = len(self.entries) # update count in header

        # move pointer to start (or end) of miptex wad
        fp.seek(texdump_offset)
        # dump miptex of dumpable entries
        for entry in entries_to_dump:
            entry.offset = fp.tell()
            entry.size = entry.sizeondisk = entry._miptex.dump(fp)

        # now towards the end, dump the directory entries
        self.header.dir_offset = fp.tell()
        fp.write(b"".join([entry.encode() for entry in self.entries]))

        # finally go to the start and write the header
        fp.seek(0)
        self.header.dump(fp)


    def add_image(self, img:Image, name:str):
        new_entry = WadDirEntry(name=name)
        new_entry._miptex = MipTex.from_image(img, name)
        self.entries.append(new_entry)

    def remove(self, entry:WadDirEntry|int|str):
        ''' remove items by index, name, or entry
        '''
        if isinstance(entry,str): # string == name of entry
            for match in filter(lambda x:x.name == entry, self.entries):
                self.entries.remove(match)
        elif isinstance(entry,WadDirEntry): # entry object, use remove()
            self.entries.remove(entry)
        else: # integer, use pop()
            self.entries.pop(entry)

    @property
    def entrynames(self):
        # returns a set. len(self.entrynames) may be != len(self.entries)
        return set(map(lambda x: x.name, self.entries))
