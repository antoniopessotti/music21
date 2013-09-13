# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         base.py
# Purpose:      music21 classes for representing score and work meta-data
#
# Authors:      Christopher Ariza
#               Michael Scott Cuthbert
#
# Copyright:    Copyright © 2010, 2012 Michael Scott Cuthbert and the music21
#               Project 
# License:      LGPL, see license.txt
#-------------------------------------------------------------------------------


import os
import re
import unittest

from music21 import base
from music21 import common
from music21 import freezeThaw
from music21 import exceptions21


#------------------------------------------------------------------------------


from music21 import environment
environLocal = environment.Environment(os.path.basename(__file__))


#------------------------------------------------------------------------------


class Metadata(base.Music21Object):
    r'''
    Metadata represent data for a work or fragment, including title, composer,
    dates, and other relevant information.

    Metadata is a :class:`~music21.base.Music21Object` subclass, meaing that it
    can be positioned on a Stream by offset and have a
    :class:`~music21.duration.Duration`.

    In many cases, each Stream will have a single Metadata object at the zero
    offset position.

    ::

        >>> md = metadata.Metadata(title='Concerto in F')
        >>> md.title
        'Concerto in F'
    
    ::

        >>> md = metadata.Metadata(otl='Concerto in F') # can use abbreviations
        >>> md.title
        'Concerto in F'

    ::

        >>> md.setWorkId('otl', 'Rhapsody in Blue')
        >>> md.otl
        'Rhapsody in Blue'

    ::

        >>> md.title
        'Rhapsody in Blue'

    '''

    ### CLASS VARIABLES ###

    classSortOrder = -10 

    # !!!OTL: Title. 
    # !!!OTP: Popular Title.
    # !!!OTA: Alternative title.
    # !!!OPR: Title of larger (or parent) work 
    # !!!OAC: Act number.
    # !!!OSC: Scene number.
    # !!!OMV: Movement number.
    # !!!OMD: Movement designation or movement name. 
    # !!!OPS: Opus number. 
    # !!!ONM: Number.
    # !!!OVM: Volume.
    # !!!ODE: Dedication. 
    # !!!OCO: Commission
    # !!!GTL: Group Title. 
    # !!!GAW: Associated Work. 
    # !!!GCO: Collection designation. 
    # !!!TXO: Original language of vocal/choral text. 
    # !!!TXL: Language of the encoded vocal/choral text. 
    # !!!OCY: Country of composition. 
    # !!!OPC: City, town or village of composition. 

    workIdAbbreviationDict = {
        'otl' : 'title',
        'otp' : 'popularTitle',
        'ota' : 'alternativeTitle',
        'opr' : 'parentTitle',
        'oac' : 'actNumber',

        'osc' : 'sceneNumber',
        'omv' : 'movementNumber',
        'omd' : 'movementName',
        'ops' : 'opusNumber',
        'onm' : 'number',

        'ovm' : 'volume',
        'ode' : 'dedication',
        'oco' : 'commission',
        'gtl' : 'groupTitle',
        'gaw' : 'associatedWork',

        'gco' : 'collectionDesignation',
        'txo' : 'textOriginalLanguage',
        'txl' : 'textLanguage',

        'ocy' : 'countryOfComposition',
        'opc' : 'localeOfComposition', # origin in abc
        }

    workIdLookupDict = {}
    for key, value in workIdAbbreviationDict.items(): 
        workIdLookupDict[value.lower()] = key

    ### INITIALIZER ###

    def __init__(self, *args, **keywords):
        from music21 import metadata

        base.Music21Object.__init__(self)

        # a list of Contributor objects
        # there can be more than one composer, or any other combination
        self._contributors = []
        self._date = None

        # store one or more URLs from which this work came; this could
        # be local file paths or otherwise
        self._urls = []

        # TODO: need a specific object for copyright and imprint
        self._imprint = None
        self._copyright = None

        # a dictionary of Text elements, where keys are work id strings
        # all are loaded with None by default
        self._workIds = {}
        for abbreviation, workId in self.workIdAbbreviationDict.iteritems():
            #abbreviation = workIdToAbbreviation(id)
            if workId in keywords:
                self._workIds[workId] = metadata.Text(keywords[workId])
            elif abbreviation in keywords:
                self._workIds[workId] = metadata.Text(keywords[abbreviation])
            else:
                self._workIds[workId] = None

        # search for any keywords that match attributes 
        # these are for direct Contributor access, must have defined
        # properties
        for attr in ['composer', 'date', 'title']:
            if attr in keywords:
                setattr(self, attr, keywords[attr])
        
        # used for the search() methods to determine what attributes
        # are made available by default; add more as properties/import 
        # exists
        self._searchAttributes = [
            'date', 
            'title', 
            'alternativeTitle', 
            'movementNumber', 
            'movementName', 
            'number', 
            'opusNumber', 
            'composer', 
            'localeOfComposition',
            ]

    ### SPECIAL METHODS ###

    def __getattr__(self, name):
        r'''
        Utility attribute access for attributes that do not yet have property
        definitions. 
        '''
        match = None
        for abbreviation, workId in self.workIdAbbreviationDict.iteritems():
        #for id in WORK_IDS:
            #abbreviation = workIdToAbbreviation(id)
            if name == workId:
                match = workId 
                break
            elif name == abbreviation:
                match = workId 
                break
        if match is None:
            raise AttributeError('object has no attribute: %s' % name)
        post = self._workIds[match]
        # always return string representation for now
        return str(post)

    ### PUBLIC METHODS ###

    @staticmethod
    def abbreviationToWorkId(abbreviation):
        '''Get work id abbreviations.

        ::

            >>> metadata.Metadata.abbreviationToWorkId('otl')
            'title'

        ::

            >>> for id in metadata.Metadata.workIdAbbreviationDict.keys():
            ...    post = metadata.Metadata.abbreviationToWorkId(id)
            ...

        '''
        abbreviation = abbreviation.lower()
        if abbreviation not in Metadata.workIdAbbreviationDict:
            raise exceptions21.MetadataException(
                'no such work id: %s' % abbreviation)
        return Metadata.workIdAbbreviationDict[abbreviation]

    def addContributor(self, c):
        r'''
        Assign a :class:`~music21.metadata.Contributor` object to this
        Metadata.

        ::

            >>> md = metadata.Metadata(title='Third Symphony')
            >>> c = metadata.Contributor()
            >>> c.name = 'Beethoven, Ludwig van'
            >>> c.role = 'composer'
            >>> md.addContributor(c)
            >>> md.composer
            'Beethoven, Ludwig van'

        ::

            >>> md.composer = 'frank'
            >>> md.composers
            ['Beethoven, Ludwig van', 'frank']

        '''
        from music21 import metadata
        if not isinstance(c, metadata.Contributor):
            raise exceptions21.MetadataException(
                'supplied object is not a Contributor: %s' % c)
        self._contributors.append(c)

    def getContributorsByRole(self, value):
        r'''
        Return a :class:`~music21.metadata.Contributor` if defined for a
        provided role. 
        
        ::

            >>> md = metadata.Metadata(title='Third Symphony')

        ::

            >>> c = metadata.Contributor()
            >>> c.name = 'Beethoven, Ludwig van'
            >>> c.role = 'composer'
            >>> md.addContributor(c)
            >>> cList = md.getContributorsByRole('composer')
            >>> cList[0].name
            'Beethoven, Ludwig van'
        
        Some musicxml files have contributors with no role defined.  To get
        these contributors, search for getContributorsByRole(None).  N.B. upon
        output to MusicXML, music21 gives these contributors the generic role
        of "creator"
        
        ::

            >>> c2 = metadata.Contributor()
            >>> c2.name = 'Beth Hadley'
            >>> md.addContributor(c2)
            >>> noRoleList = md.getContributorsByRole(None)
            >>> len(noRoleList)
            1

        ::

            >>> noRoleList[0].role
            >>> noRoleList[0].name
            'Beth Hadley'
        
        '''
        post = [] # there may be more than one per role
        for c in self._contributors:
            if c.role == value:
                post.append(c)
        if len(post) > 0:
            return post 
        else:
            return None

    def search(self, query, field=None):
        r'''
        Search one or all fields with a query, given either as a string or a
        regular expression match.

        ::

            >>> md = metadata.Metadata()
            >>> md.composer = 'Beethoven, Ludwig van'
            >>> md.title = 'Third Symphony'

        ::

            >>> md.search('beethoven', 'composer')
            (True, 'composer')
        
        ::

            >>> md.search('beethoven', 'compose')
            (True, 'composer')

        ::

            >>> md.search('frank', 'composer')
            (False, None)

        ::

            >>> md.search('frank')
            (False, None)

        ::

            >>> md.search('third')
            (True, 'title')

        ::

            >>> md.search('third', 'composer')
            (False, None)

        ::

            >>> md.search('third', 'title')
            (True, 'title')

        ::

            >>> md.search('third|fourth')
            (True, 'title')

        ::

            >>> md.search('thove(.*)')
            (True, 'composer')

        '''
        valueFieldPairs = []
        if field != None:
            match = False
            try:
                value = getattr(self, field)
                valueFieldPairs.append((value, field))
                match = True
            except AttributeError:
                pass
            if not match:
                for f in self._searchAttributes:
                    #environLocal.printDebug(['comparing fields:', f, field])
                    # look for partial match in all fields
                    if field.lower() in f.lower():
                        value = getattr(self, f)
                        valueFieldPairs.append((value, f))
                        match = True
                        break
            # if cannot find a match for any field, return 
            if not match:
                return False, None
        else: # get all fields
            for f in self._searchAttributes:
                value = getattr(self, f)
                valueFieldPairs.append((value, f))
        # for now, make all queries strings
        # ultimately, can look for regular expressions by checking for
        # .search
        useRegex = False
        if hasattr(query, 'search'):
            useRegex = True
            reQuery = query # already compiled
        # look for regex characters
        elif common.isStr(query) and \
            any(character in query for character in '*.|+?{}'):
            useRegex = True
            reQuery = re.compile(query, flags=re.I) 
        if useRegex:
            for v, f in valueFieldPairs:
                # re.I makes case insensitive
                match = reQuery.search(str(v))
                if match is not None:
                    return True, f
        else:
            query = str(query)
            for v, f in valueFieldPairs:
                if common.isStr(v):
                    if query.lower() in v.lower():
                        return True, f
                elif query == v: 
                    return True, f
        return False, None
            
    def setWorkId(self, idStr, value):
        r'''
        Directly set a workd id, given either as a full string name or as a
        three character abbreviation. The following work id abbreviations and
        their full id string are given as follows. In many cases the Metadata
        object support properties for convenient access to these work ids. 

        Id abbreviations and strings: otl / title, otp / popularTitle, ota /
        alternativeTitle, opr / parentTitle, oac / actNumber, osc /
        sceneNumber, omv / movementNumber, omd / movementName, ops /
        opusNumber, onm / number, ovm / volume, ode / dedication, oco /
        commission, gtl / groupTitle, gaw / associatedWork, gco /
        collectionDesignation, txo / textOriginalLanguage, txl / textLanguage,
        ocy / countryOfComposition, opc / localeOfComposition.
        
        ::

            >>> md = metadata.Metadata(title='Quartet')
            >>> md.title
            'Quartet'

        ::

            >>> md.setWorkId('otl', 'Trio')
            >>> md.title
            'Trio'

        ::

            >>> md.setWorkId('sdf', None)
            Traceback (most recent call last):
            MetadataException: no work id available with id: sdf

        '''
        from music21 import metadata
        idStr = idStr.lower()
        match = False
        for abbreviation, workId in self.workIdAbbreviationDict.iteritems():
        #for id in WORK_IDS:
            #abbreviation = workIdToAbbreviation(id)
            if workId.lower() == idStr:
                self._workIds[workId] = metadata.Text(value)
                match = True
                break
            elif abbreviation == idStr:
                self._workIds[workId] = metadata.Text(value)
                match = True
                break
        if not match:
            raise exceptions21.MetadataException(
                'no work id available with id: %s' % idStr)

    @staticmethod
    def workIdToAbbreviation(value):
        '''Get a work abbreviation from a string representation.

        ::

            >>> metadata.Metadata.workIdToAbbreviation('localeOfComposition')
            'opc'

        ::

            >>> for n in metadata.Metadata.workIdAbbreviationDict.values():
            ...     post = metadata.Metadata.workIdToAbbreviation(n)
            ...

        '''
        # NOTE: this is a performance critical function
        try:
            # try direct access, where keys are already lower case
            return Metadata.workIdLookupDict[value] 
        except KeyError:
            pass

        # slow approach
        for workId in Metadata.workIdAbbreviationDict.keys():
            if value.lower() == Metadata.workIdAbbreviationDict[workId].lower():
                return workId
        raise exceptions21.MetadataException(
            'no such work id: %s' % value)

    ### PUBLIC PROPERTIES ###

    @apply
    def alternativeTitle(): # @NoSelf
        def fget(self):
            r'''
            Get or set the alternative title. 
            
            ::

                >>> md = metadata.Metadata(popularTitle='Eroica')
                >>> md.alternativeTitle = 'Heroic Symphony'
                >>> md.alternativeTitle
                'Heroic Symphony'

            '''
            post = self._workIds['alternativeTitle']
            if post == None:
                return None
            return str(self._workIds['alternativeTitle'])
        def fset(self, value):
            from music21 import metadata
            self._workIds['alternativeTitle'] = metadata.Text(value)
        return property(**locals())

    @apply
    def composer(): # @NoSelf
        def fget(self):
            r'''
            Get or set the composer of this work. More than one composer may be
            specified.

            The composer attribute does not live in Metadata, but creates a
            :class:`~music21.metadata.Contributor` object in the Metadata
            object.
            
            ::

                >>> md = metadata.Metadata(
                ...     title='Third Symphony',
                ...     popularTitle='Eroica', 
                ...     composer='Beethoven, Ludwig van',
                ...     )
                >>> md.composer
                'Beethoven, Ludwig van'

            '''
            post = self.getContributorsByRole('composer')
            if post == None:
                return None
            # get just the name of the first composer
            return str(post[0].name)
        def fset(self, value):
            from music21 import metadata
            c = metadata.Contributor()
            c.name = value
            c.role = 'composer'
            self._contributors.append(c)
        return property(**locals())

    @property
    def composers(self):
        r'''
        Get a list of all :class:`~music21.metadata.Contributor` objects
        defined as composer of this work.
        '''
        post = self.getContributorsByRole('composer')
        if post == None:
            return None
        # get just the name of the first composer
        return [x.name for x in post]

    @apply
    def date(): # @NoSelf
        def fget(self):
            r'''
            Get or set the date of this work as one of the following date objects:
            :class:`~music21.metadata.DateSingle`,
            :class:`~music21.metadata.DateRelative`,
            :class:`~music21.metadata.DateBetween`,
            :class:`~music21.metadata.DateSelection`, 
            
            ::

                >>> md = metadata.Metadata(
                ...     title='Third Symphony', 
                ...     popularTitle='Eroica', 
                ...     composer='Beethoven, Ludwig van',
                ...     )
                >>> md.date = '2010'
                >>> md.date
                '2010/--/--'

            ::

                >>> md.date = metadata.DateBetween(['2009/12/31', '2010/1/28'])
                >>> md.date
                '2009/12/31 to 2010/01/28'

            '''
            return str(self._date)
        def fset(self, value):
            from music21 import metadata
            if isinstance(value, metadata.DateSingle): # all inherit date single
                self._date = value
            else:
                ds = metadata.DateSingle(value) # assume date single; could be other sublcass
                self._date = ds
        return property(**locals())

    @apply
    def localeOfComposition():  # @NoSelf
        def fget(self):
            r'''
            Get or set the locale of composition, or origin, of the work. 
            '''
            post = self._workIds['localeOfComposition']
            if post == None:
                return None
            return str(self._workIds['localeOfComposition'])
        def fset(self, value):
            from music21 import metadata
            self._workIds['localeOfComposition'] = metadata.Text(value)
        return property(**locals())

    @apply
    def movementName(): # @NoSelf
        def fget(self):
            r'''
            Get or set the movement title. 
            
            Note that a number of pieces from various MusicXML datasets have the piece title as the movement title.
            For instance, the Bach Chorales, since they are technically movements of larger cantatas.
            '''
            post = self._workIds['movementName']
            if post == None:
                return None
            return str(self._workIds['movementName'])
        def fset(self, value):
            from music21 import metadata
            self._workIds['movementName'] = metadata.Text(value)
        return property(**locals())

    @apply
    def movementNumber(): # @NoSelf
        def fget(self):
            r'''
            Get or set the movement number. 
            '''
            post = self._workIds['movementNumber']
            if post == None:
                return None
            return str(self._workIds['movementNumber'])
        def fset(self, value):
            from music21 import metadata
            self._workIds['movementNumber'] = metadata.Text(value)
        return property(**locals())

    @apply
    def number(): # @NoSelf
        def fget(self):
            r'''
            Get or set the number of the work.  
            
            TODO: Explain what this means...
            '''
            post = self._workIds['number']
            if post == None:
                return None
            return str(self._workIds['number'])
        def fset(self, value):
            from music21 import metadata
            self._workIds['number'] = metadata.Text(value)
        return property(**locals())

    @apply
    def opusNumber(): # @NoSelf
        def fget(self):
            r'''
            Get or set the opus number. 
            '''
            post = self._workIds['opusNumber']
            if post == None:
                return None
            return str(self._workIds['opusNumber'])
        def fset(self, value):
            from music21 import metadata
            self._workIds['opusNumber'] = metadata.Text(value)
        return property(**locals())

    @apply
    def title(): # @NoSelf
        def fget(self):
            r'''
            Get the title of the work, or the next-matched title string
            available from a related parameter fields. 

            ::

                >>> md = metadata.Metadata(title='Third Symphony')
                >>> md.title
                'Third Symphony'
            
            ::

                >>> md = metadata.Metadata(popularTitle='Eroica')
                >>> md.title
                'Eroica'
            
            ::

                >>> md = metadata.Metadata(
                ...     title='Third Symphony', 
                ...     popularTitle='Eroica',
                ...     )
                >>> md.title
                'Third Symphony'

            ::

                >>> md.popularTitle
                'Eroica'

            ::

                >>> md.otp
                'Eroica'

            '''
            searchId = ['title', 'popularTitle', 'alternativeTitle', 'movementName']
            post = None
            for key in searchId:
                post = self._workIds[key]
                if post != None: # get first matched
                    # get a string from this Text object
                    # get with normalized articles
                    return self._workIds[key].getNormalizedArticle()
        def fset(self, value):
            from music21 import metadata
            self._workIds['title'] = metadata.Text(value)
        return property(**locals())


#-------------------------------------------------------------------------------


class RichMetadata(Metadata):
    r'''
    RichMetadata adds to Metadata information about the contents of the Score
    it is attached to. TimeSignature, KeySignature and related analytical is
    stored.  RichMetadata are generally only created in the process of creating
    stored JSON metadata. 

    ::

        >>> richMetadata = metadata.RichMetadata(title='Concerto in F')
        >>> richMetadata.title
        'Concerto in F'

    ::

        >>> richMetadata.keySignatureFirst = key.KeySignature(-1)
        >>> 'keySignatureFirst' in richMetadata._searchAttributes
        True

    '''

    ### INITIALIZER ###

    def __init__(self, *args, **keywords):
        Metadata.__init__(self, *args, **keywords)
        self.ambitus = None
        self.keySignatureFirst = None
        self.keySignatures = []
        self.noteCount = None
        self.pitchHighest = None
        self.pitchLowest = None
        self.quarterLength = None
        self.tempoFirst = None
        self.tempos = []
        self.timeSignatureFirst = None
        self.timeSignatures = []
        # append to existing search attributes from Metdata
        self._searchAttributes += [
            'keySignatureFirst', 'timeSignatureFirst', 'pitchHighest', 
            'pitchLowest', 'noteCount', 'quarterLength',
            ]

    ### PUBLIC METHODS ###

    def merge(self, other, favorSelf=False):
        r'''
        Given another Metadata or RichMetadata object, combine
        all attributes and return a new object.

        ::

            >>> md = metadata.Metadata(title='Concerto in F')
            >>> md.title
            'Concerto in F'

        ::

            >>> richMetadata = metadata.RichMetadata()
            >>> richMetadata.merge(md)
            >>> richMetadata.title
            'Concerto in F'

        '''
        # specifically name attributes to copy, as do not want to get all
        # Metadata is a m21 object
        localNames = [
            '_contributors', '_date', '_urls', '_imprint', '_copyright', 
            '_workIds',
            ]
        environLocal.printDebug(['RichMetadata: calling merge()'])
        for name in localNames: 
            localValue = getattr(self, name)
            # if not set, and favoring self, then only then set
            # this will not work on dictionaries
            if localValue != None and favorSelf:
                continue
            else:
                try:
                    if other is not None:
                        otherValue = getattr(other, name)
                        if otherValue is not None:
                            setattr(self, name, otherValue)
                except AttributeError:
                    pass

    def update(self, streamObj):
        r'''
        Given a Stream object, update attributes with stored objects. 
        '''
        environLocal.printDebug(['RichMetadata: update(): start'])
        
        # clear all old values
        self.keySignatureFirst = None
        #self.keySignatures = []
        self.timeSignatureFirst = None
        #self.timeSignatures = []
        self.tempoFirst = None
        #self.tempos = []

        self.noteCount = None
        self.quarterLength = None

        self.ambitus = None
        self.pitchHighest = None
        self.pitchLowest = None

        # get flat sorted stream
        flat = streamObj.flat.sorted

        tsStream = flat.getElementsByClass('TimeSignature')
        if len(tsStream) > 0:
            # just store the string representation  
            # re-instantiating TimeSignature objects is expensive
            self.timeSignatureFirst = tsStream[0].ratioString
        
        # this presently does not work properly b/c ts comparisons are not
        # built-in; need to add __eq__ methods to MeterTerminal
#         for ts in tsStream:
#             if ts not in self.timeSignatures:
#                 self.timeSignatures.append(ts)

        ksStream = flat.getElementsByClass('KeySignature')
        if len(ksStream) > 0:
            self.keySignatureFirst = str(ksStream[0])
#         for ks in ksStream:
#             if ks not in self.keySignatures:
#                 self.keySignatures.append(ts)

        self.noteCount = len(flat.notesAndRests)
        self.quarterLength = flat.highestTime

# commenting out temporarily due to memory error     
# with corpus/beethoven/opus132.xml
#         # must be a method-level import
#         from music21.analysis import discrete
   
#         environLocal.printDebug(['RichMetadata: update(): calling discrete.Ambitus(streamObj)'])
# 
#         analysisObj = discrete.Ambitus(streamObj)    
#         psRange = analysisObj.getPitchSpan(streamObj)
#         if psRange != None: # may be none if no pitches are stored
#             # presently, these are numbers; convert to pitches later
#             self.pitchLowest = str(psRange[0]) 
#             self.pitchHighest = str(psRange[1])
# 
#         self.ambitus = analysisObj.getSolution(streamObj)


#------------------------------------------------------------------------------


class Test(unittest.TestCase):

    # When `maxDiff` is None, `assertMultiLineEqual()` provides better errors.
    maxDiff = None

    def runTest(self):
        pass

    def testMetadataLoadCorpus(self):
        from music21.musicxml import xmlHandler
        from music21.musicxml import testFiles as mTF
        from music21.musicxml import fromMxObjects

        d = xmlHandler.Document()
        d.read(mTF.mozartTrioK581Excerpt) #@UndefinedVariable
        mxScore = d.score # get the mx score directly
        md = fromMxObjects.mxScoreToMetadata(mxScore)

        self.assertEqual(md.movementNumber, '3')
        self.assertEqual(md.movementName, 'Menuetto (Excerpt from Second Trio)')
        self.assertEqual(md.title, 'Quintet for Clarinet and Strings')
        self.assertEqual(md.number, 'K. 581')
        # get contributors directly from Metadata interface
        self.assertEqual(md.composer, 'Wolfgang Amadeus Mozart')

        d.read(mTF.binchoisMagnificat) # @UndefinedVariable
        mxScore = d.score # get the mx score directly
        md = fromMxObjects.mxScoreToMetadata(mxScore)
        self.assertEqual(md.composer, 'Gilles Binchois')

    def testJSONSerializationMetadata(self):
        from music21.musicxml import xmlHandler
        from music21.musicxml import fromMxObjects
        from music21.musicxml import testFiles
        from music21 import metadata

        md = metadata.Metadata(title='Concerto in F', date='2010', composer='Frank')
        #environLocal.printDebug([str(md.json)])
        self.assertEqual(md.composer, 'Frank')

        #md.jsonPrint()

        mdNew = metadata.Metadata()
        
        jsonString = freezeThaw.JSONFreezer(md).json
        freezeThaw.JSONThawer(mdNew).json = jsonString

        self.assertEqual(mdNew.date, '2010/--/--')
        self.assertEqual(mdNew.composer, 'Frank')

        self.assertEqual(mdNew.title, 'Concerto in F')

        # test getting meta data from an imported source

        d = xmlHandler.Document()
        d.read(testFiles.mozartTrioK581Excerpt) # @UndefinedVariable
        mxScore = d.score # get the mx score directly

        md = fromMxObjects.mxScoreToMetadata(mxScore)

        self.assertEqual(md.movementNumber, '3')
        self.assertEqual(md.movementName, 'Menuetto (Excerpt from Second Trio)')
        self.assertEqual(md.title, 'Quintet for Clarinet and Strings')
        self.assertEqual(md.number, 'K. 581')
        self.assertEqual(md.composer, 'Wolfgang Amadeus Mozart')

        # convert to json and see if data is still there
        #md.jsonPrint()
        mdNew = metadata.Metadata()

        jsonString = freezeThaw.JSONFreezer(md).json
        freezeThaw.JSONThawer(mdNew).json = jsonString

        self.assertEqual(mdNew.movementNumber, '3')
        self.assertEqual(mdNew.movementName, 'Menuetto (Excerpt from Second Trio)')
        self.assertEqual(mdNew.title, 'Quintet for Clarinet and Strings')
        self.assertEqual(mdNew.number, 'K. 581')
        self.assertEqual(mdNew.composer, 'Wolfgang Amadeus Mozart')

    def testRichMetadata(self):
        from music21 import corpus
        from music21 import metadata

        score = corpus.parse('jactatur')
        self.assertEqual(score.metadata.composer, 'Johannes Ciconia')

        richMetadata = metadata.RichMetadata()
        richMetadata.merge(score.metadata)

        self.assertEqual(richMetadata.composer, 'Johannes Ciconia')
        # update richMetadata with stream
        richMetadata.update(score)

        self.assertEqual(richMetadata.keySignatureFirst, '<music21.key.KeySignature of 1 flat, mode major>')

        self.assertEqual(str(richMetadata.timeSignatureFirst), '2/4')

        rmdNew = metadata.RichMetadata()

        jsonString = freezeThaw.JSONFreezer(richMetadata).json
        freezeThaw.JSONThawer(rmdNew).json = jsonString
        
        self.assertEqual(rmdNew.composer, 'Johannes Ciconia')

        self.assertEqual(str(rmdNew.timeSignatureFirst), '2/4')
        self.assertEqual(str(rmdNew.keySignatureFirst), '<music21.key.KeySignature of 1 flat, mode major>')

#         self.assertEqual(richMetadata.pitchLowest, 55)
#         self.assertEqual(richMetadata.pitchHighest, 65)
#         self.assertEqual(str(richMetadata.ambitus), '<music21.interval.Interval m7>')

        score = corpus.parse('bwv66.6')
        richMetadata = metadata.RichMetadata()
        richMetadata.merge(score.metadata)

        richMetadata.update(score)
        self.assertEqual(str(richMetadata.keySignatureFirst), '<music21.key.KeySignature of 3 sharps, mode minor>')
        self.assertEqual(str(richMetadata.timeSignatureFirst), '4/4')

        jsonString = freezeThaw.JSONFreezer(richMetadata).json
        freezeThaw.JSONThawer(rmdNew).json = jsonString

        self.assertEqual(str(rmdNew.timeSignatureFirst), '4/4')
        self.assertEqual(str(rmdNew.keySignatureFirst), '<music21.key.KeySignature of 3 sharps, mode minor>')

    def testWorkIds(self):
        from music21 import corpus
        from music21 import metadata

        opus = corpus.parse('essenFolksong/teste')
        self.assertEqual(len(opus), 8)

        score = opus.getScoreByNumber(4)
        self.assertEqual(score.metadata.localeOfComposition,
            'Asien, Ostasien, China, Sichuan')

        richMetadata = metadata.RichMetadata()
        richMetadata.merge(score.metadata)
        richMetadata.update(score)

        self.assertEqual(richMetadata.localeOfComposition, 
            'Asien, Ostasien, China, Sichuan')

    def testMetadataSearch(self):
        from music21 import corpus
        score = corpus.parse('ciconia')
        self.assertEqual(
            score.metadata.search('quod', 'title'), 
            (True, 'title'))
        self.assertEqual(
            score.metadata.search('qu.d', 'title'), 
            (True, 'title'))
        self.assertEqual(
            score.metadata.search(re.compile('(.*)canon(.*)')), 
            (True, 'title'))

    def testRichMetadata(self):
        from music21 import corpus
        from music21 import metadata
        from music21 import test
        score = corpus.parse('bwv66.6')
        richMetadata = metadata.RichMetadata()
        richMetadata.merge(score.metadata)
        richMetadata.update(score)
        self.assertEqual(richMetadata.noteCount, 165)
        self.assertEqual(richMetadata.quarterLength, 36.0)
        self.assertMultiLineEqual(
            freezeThaw.JSONFreezer(richMetadata).prettyJson,
            test.dedent('''
                {
                    "__attr__": {
                        "_contributors": [], 
                        "_urls": [], 
                        "_workIds": {
                            "movementName": {
                                "__attr__": {
                                    "_data": "bwv66.6.mxl"
                                }, 
                                "__class__": "music21.metadata.primitives.Text"
                            }
                        }, 
                        "keySignatureFirst": "<music21.key.KeySignature of 3 sharps, mode minor>", 
                        "noteCount": 165, 
                        "quarterLength": 36.0, 
                        "timeSignatureFirst": "4/4"
                    }, 
                    "__class__": "music21.metadata.base.RichMetadata", 
                    "__version__": [
                        ''' + str(base.VERSION[0]) + ''', 
                        ''' + str(base.VERSION[1]) + ''', 
                        ''' + str(base.VERSION[2]) + '''
                    ]
                }
                ''',
                ))

#------------------------------------------------------------------------------


_DOC_ORDER = ()

__all__ = [
    'Metadata',
    'RichMetadata',
    ]

if __name__ == "__main__":
    import music21
    music21.mainTest(Test)


#------------------------------------------------------------------------------