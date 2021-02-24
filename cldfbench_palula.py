from collections import ChainMap
import pathlib

from pydictionaria.sfm_lib import Database as SFM, Entry
from pydictionaria import sfm2cldf

from cldfbench import CLDFSpec, Dataset as BaseDataset

"""
 lx             Palula lexeme (lexical representation) = main entry
 +-  hm         Homonym number
 +-  va         Variant form, usually (but not exclusively) a phonological variant form
 |   |          used within the target dialect or in the other main dialect
 |   +-  ve     The domain of the form in  va, usually the name of the geographical
 |              location, e.g. Biori
 +-  se         Used liberally for multi-word constructions in which the lexeme occurs
     +-  ph     Phonetic form (surface representation)
     +-  gv     Vernacular form
     +-  mn     Reference to a main entry, especially in cases where a variant form or an
     |          irregular form needs a separate listing
     +-  mr     Morphemic form (underlying representation, if different from lexical)
     +-  xv     Example phrase or sentence
     |   +-  xe Translation of above  xv
     |   +-  xvm Morphemes of IGT
     |   +-  xeg Gloss of IGT
     +-  bw     Indicating that it is a borrowed word, but by using the label Comp I
     |          don’t make any specific claims as to the route of borrowing, instead just
     |          mentioning the language that has a similar form and citing the source form
     |          itself
     +-  ps     Part of speech label
         +-  pd Paradigm label (e.g. i-decl)
         |   +-  pdl    Specifying the form category of the following pdv
         |       +-  pdv    The word form
         +-  sn Sense number (for a lexeme having clearly different senses). I use this
             |  very sparingly, trying to avoid too much of an English or Western bias
             +-  re Word(s) used in English (reversed) index.
             +-  de Gloss(es) or multi-word definition
             +-  oe Restrictions, mainly grammatical (e.g. With plural reference)
             +-  ue Usage (semantic or grammatical)
             +-  cf Cross-reference, linking it to another main entry
             +-  et Old Indo-Aryan proto-form (I’m restricting this to Turner 1966)
                 +-  eg The published gloss of  et
                 +-  es The reference to Turner, always in the form T: (referring to the
                        entry number in Turner, not the page number)
"""


def reorganize(sfm):
    return sfm


def preprocess(entry):
    new = Entry()
    for i, (marker, content) in enumerate(entry):
        if marker == 'pd':
            try:
                j = i + 1
                while entry[j][0] == 'pdl':
                    if j > i + 1:
                        content += ','
                    content += ' ({0})'.format(entry[j][1])
                    if entry[j + 1][0] == 'pdv':
                        content += ': {0}'.format(entry[j + 1][1])
                    j += 2
            except IndexError:
                pass
        if marker == 'bw':
            try:
                ve = entry[i + 1]
                if ve[0] == 'bwv' and ve[1] != content:
                    content += ": %s" % ve[1]
            except IndexError:
                pass
        if marker == 'va':
            try:
                ve = entry[i + 1]
                if ve[0] == 've' and ve[1] != content:
                    content += " (%s)" % ve[1]
            except IndexError:
                pass
        if marker == 'et':
            try:
                eg = entry[i + 1]
                if eg[0] == 'eg':
                    content += " '%s'" % eg[1]
            except IndexError:
                pass
            try:
                es = entry[i + 2]
                if es[0] == 'es':
                    content += " (%s)" % es[1]
            except IndexError:
                pass
        new.append((marker, content))

    return new


def authors_string(authors):
    def is_primary(a):
        return not isinstance(a, dict) or a.get('primary', True)

    primary = ' and '.join(
        a['name'] if isinstance(a, dict) else a
        for a in authors
        if is_primary(a))
    secondary = ' and '.join(
        a['name']
        for a in authors
        if not is_primary(a))
    if primary and secondary:
        return '{} with {}'.format(primary, secondary)
    else:
        return primary or secondary


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "palula"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return CLDFSpec(
            dir=self.cldf_dir,
            module='Dictionary',
            metadata_fname='cldf-metadata.json')

    def cmd_download(self, args):
        """
        Download files to the raw/ directory. You can use helpers methods of `self.raw_dir`, e.g.

        >>> self.raw_dir.download(url, fname)
        """
        pass

    def cmd_makecldf(self, args):
        """
        Convert the raw data to a CLDF dataset.

        >>> args.writer.objects['LanguageTable'].append(...)
        """

        # read data

        md = self.etc_dir.read_json('md.json')
        properties = md.get('properties') or {}
        language_name = md['language']['name']
        isocode = md['language']['isocode']
        language_id = md['language']['isocode']
        glottocode = md['language']['glottocode']

        marker_map = ChainMap(
            properties.get('marker_map') or {},
            sfm2cldf.DEFAULT_MARKER_MAP)
        entry_sep = properties.get('entry_sep') or sfm2cldf.DEFAULT_ENTRY_SEP
        sfm = SFM(
            self.raw_dir / 'db.sfm',
            marker_map=marker_map,
            entry_sep=entry_sep)

        examples = sfm2cldf.load_examples(self.raw_dir / 'examples.sfm')

        if (self.etc_dir / 'cdstar.json').exists():
            media_catalog = self.etc_dir.read_json('cdstar.json')
        else:
            media_catalog = {}

        # preprocessing

        sfm = reorganize(sfm)
        sfm.visit(preprocess)

        # processing

        with open(self.dir / 'cldf.log', 'w', encoding='utf-8') as log_file:
            log_name = '%s.cldf' % language_id
            cldf_log = sfm2cldf.make_log(log_name, log_file)

            entries, senses, examples, media = sfm2cldf.process_dataset(
                self.id, language_id, properties,
                sfm, examples, media_catalog=media_catalog,
                glosses_path=self.raw_dir / 'glosses.flextext',
                examples_log_path=self.dir / 'examples.log',
                glosses_log_path=self.dir / 'glosses.log',
                cldf_log=cldf_log)

            # good place for some post-processing

            # cldf schema

            sfm2cldf.make_cldf_schema(
                args.writer.cldf, properties,
                entries, senses, examples, media)

            sfm2cldf.attach_column_titles(args.writer.cldf, properties)

            print(file=log_file)

            entries = sfm2cldf.ensure_required_columns(
                args.writer.cldf, 'EntryTable', entries, cldf_log)
            senses = sfm2cldf.ensure_required_columns(
                args.writer.cldf, 'SenseTable', senses, cldf_log)
            examples = sfm2cldf.ensure_required_columns(
                args.writer.cldf, 'ExampleTable', examples, cldf_log)
            media = sfm2cldf.ensure_required_columns(
                args.writer.cldf, 'media.csv', media, cldf_log)

            entries = sfm2cldf.remove_senseless_entries(
                senses, entries, cldf_log)

        # output

        args.writer.cldf.properties['dc:creator'] = authors_string(
            md.get('authors') or ())

        language = {
            'ID': language_id,
            'Name': language_name,
            'ISO639P3code': isocode,
            'Glottocode': glottocode,
        }
        args.writer.objects['LanguageTable'] = [language]

        args.writer.objects['EntryTable'] = entries
        args.writer.objects['SenseTable'] = senses
        args.writer.objects['ExampleTable'] = examples
        args.writer.objects['media.csv'] = media
