# -*- coding: UTF-8 -*-

import os
import re
import sys
import xbmc
import urllib
import socket
import shutil
import xbmcgui
import unicodedata
from utilities import *

try:
  import xbmcvfs
  VFS = True
except:
  VFS = False  

STATUS_LABEL   = 100
LOADING_IMAGE  = 110
SUBTITLES_LIST = 120
SERVICES_LIST  = 150
CANCEL_DIALOG  = ( 9, 10, 216, 247, 257, 275, 61467, 61448, )

_              = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__settings__   = sys.modules[ "__main__" ].__settings__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__profile__    = sys.modules[ "__main__" ].__profile__ 

SERVICE_DIR    = os.path.join(__cwd__, "resources", "lib", "services")

class GUI( xbmcgui.WindowXMLDialog ):
        
  def __init__( self, *args, **kwargs ):        
    pass

  def set_allparam(self):       
    temp                = False
    rar                 = False
    self.newWindow      = True
    self.stack          = False
    self.stackSecond    = ""
    self.autoDownload   = False
    self.list           = []
    movieFullPath       = urllib.unquote(xbmc.Player().getPlayingFile())
    path                = __settings__.getSetting( "subfolder" ) == "true"                 # True for movie folder
    sub_folder          = xbmc.translatePath(__settings__.getSetting( "subfolderpath" ))

    if (movieFullPath.find("http://") > -1 ):
      temp = True

    elif (movieFullPath.find("rar://") > -1 ):
      rar = True
      movieFullPath = movieFullPath.replace("rar://","")
      if path:
        sub_folder = os.path.dirname(os.path.dirname( movieFullPath ))
    
    elif (movieFullPath.find("stack://") > -1 ):
      movieFullPath, stackSecond = movieFullPath.split(" , ")
      movieFullPath = movieFullPath[8:]
      self.stackSecond = os.path.basename(stackSecond)
      self.stack = True

    if not path:
      if len(sub_folder) < 1 :
        sub_folder = os.path.dirname( movieFullPath )

    if path and not rar:
      if sub_folder.find("smb://") > -1:
        if temp:
          dialog = xbmcgui.Dialog()
          sub_folder = dialog.browse( 0, "Choose Subtitle folder", "files")
        else:
          sub_folder = os.path.dirname( movieFullPath )
      else:
        sub_folder = os.path.dirname( movieFullPath )   

    self.year      = xbmc.getInfoLabel("VideoPlayer.Year")                  # Year
    self.season    = str(xbmc.getInfoLabel("VideoPlayer.Season"))           # Season
    self.episode   = str(xbmc.getInfoLabel("VideoPlayer.Episode"))          # Episode        
    
    if self.episode.lower().find("s") > -1:                                 # Check if season is "Special"             
      self.season = "0"                                                     #
      self.episode = self.episode[-1:]                                      #

    self.tvshow    = xbmc.getInfoLabel("VideoPlayer.TVshowtitle")           # Show
    self.title     = unicodedata.normalize('NFKD', 
                      unicode(unicode(xbmc.getInfoLabel
                      ("VideoPlayer.Title"), 'utf-8'))
                      ).encode('ascii','ignore')                            # Title

    if self.tvshow == "":
      if str(self.year) == "":
        title, season, episode = regex_tvshow(False, self.title)
        if episode != "":
          self.season = str(int(season))
          self.episode = str(int(episode))
          self.tvshow = title
        else:
          self.title, self.year = xbmc.getCleanMovieTitle( self.title )

      else:
        self.title = self.title  
    else:
      self.year = ""
    self.language_1 = toScriptLang(__settings__.getSetting( "Lang01" ))     # Full language 1
    self.language_2 = toScriptLang(__settings__.getSetting( "Lang02" ))     # Full language 2  
    self.language_3 = toScriptLang(__settings__.getSetting( "Lang03" ))     # Full language 3

    self.sub_folder = sub_folder                                            # Subtitle download folder

    self.file_original_path = urllib.unquote ( movieFullPath )              # Movie Path

    self.set_temp = temp

    if __settings__.getSetting( "disable_hash_search" ) == "true":
      self.set_temp = True

    self.mansearch =  __settings__.getSetting( "searchstr" ) == "true"      # Manual search string??
    self.parsearch =  __settings__.getSetting( "par_folder" ) == "true"     # Parent folder as search string
    self.rar = rar                                                          # rar archive?

    if (__settings__.getSetting( "fil_name" ) == "true"):                   # Display Movie name or search string
      self.file_name = os.path.basename( movieFullPath )
    else:
      if (len(str(self.year)) < 1 ) :
        self.file_name = self.title.encode('utf-8')
        if (len(self.tvshow) > 0):
          self.file_name = "%s S%.2dE%.2d" % (self.tvshow.encode('utf-8'), int(self.season), int(self.episode) )
      else:
        self.file_name = "%s (%s)" % (self.title.encode('utf-8'), str(self.year),)    

    self.tmp_sub_dir = os.path.join( __profile__ ,"sub_tmp" )

    if not self.tmp_sub_dir.endswith(':') and not os.path.exists(self.tmp_sub_dir):
      os.makedirs(self.tmp_sub_dir)
    else:
      self.rem_files(self.tmp_sub_dir)

    self.getControl( 111 ).setVisible( False )                              # check for existing subtitles and set to "True" if found
    sub_exts = ["srt", "sub", "txt", "smi", "ssa", "ass" ]
    br = 0
    for i in range(3):
      for sub_ext in sub_exts:
        if br == 0:
          exec("lang = toOpenSubtitles_two(self.language_%s)" % (str(i+1)) )
          if os.path.isfile ("%s.%s.%s" % (os.path.join(sub_folder,os.path.splitext( os.path.basename( self.file_original_path ) )[0]),lang ,sub_ext,)):
            self.getControl( 111 ).setVisible( True )
            br = 1
            break
    
    if (__settings__.getSetting( "auto_download" ) == "true") and (__settings__.getSetting( "auto_download_file" ) != os.path.basename( movieFullPath )):
        self.autoDownload = True
        __settings__.setSetting("auto_download_file", "")
             
#### ---------------------------- Set Service ----------------------------###     

    def_movie_service = __settings__.getSetting( "defmovieservice")
    def_tv_service = __settings__.getSetting( "deftvservice")
    service_list = []
    service = ""

    for name in os.listdir(SERVICE_DIR):
      if os.path.isdir(os.path.join(SERVICE_DIR,name)) and __settings__.getSetting( name ) == "true":
        service_list.append( name )
        service = name

    if len(self.tvshow) > 0:
      if service_list.count(def_tv_service) > 0:
        service = def_tv_service
    else:
      if service_list.count(def_movie_service) > 0:
        service = def_movie_service

    if len(service_list) > 0:  
      if len(service) < 1:
        self.service = service_list[0]
      else:
        self.service = service  

      self.service_list = service_list
      self.next = list(service_list)
      self.controlId = -1
      self.subtitles_list = []

      log( __name__ ,"Manual Search : [%s]"        % self.mansearch)
      log( __name__ ,"Default Service : [%s]"      % self.service)
      log( __name__ ,"Services : [%s]"             % self.service_list)
      log( __name__ ,"Temp?: [%s]"                 % self.set_temp)
      log( __name__ ,"Rar?: [%s]"                  % self.rar)
      log( __name__ ,"File Path: [%s]"             % self.file_original_path)
      log( __name__ ,"Year: [%s]"                  % str(self.year))
      log( __name__ ,"Tv Show Title: [%s]"         % self.tvshow)
      log( __name__ ,"Tv Show Season: [%s]"        % self.season)
      log( __name__ ,"Tv Show Episode: [%s]"       % self.episode)
      log( __name__ ,"Movie/Episode Title: [%s]"   % self.title)
      log( __name__ ,"Subtitle Folder: [%s]"       % self.sub_folder)
      log( __name__ ,"Languages: [%s] [%s] [%s]"   % (self.language_1, self.language_2, self.language_3,))
      log( __name__ ,"Parent Folder Search: [%s]"  % self.parsearch)
      log( __name__ ,"Stacked(CD1/CD2)?: [%s]"     % self.stack)

      try:
        self.list_services()
      except:
        self.newWindow = False
        self.list_services()

      try:
        self.Search_Subtitles()
      except:
        errno, errstr = sys.exc_info()[:2]
        self.getControl( STATUS_LABEL ).setLabel( "Error:" + " " + str(errstr) )
        xbmc.sleep(2000)
        self.exit_script()
    else:
      self.getControl( STATUS_LABEL ).setLabel( "No Services Have been selected" )
      xbmc.sleep(2000)
      self.exit_script()    

#### ---------------------------- On Init ----------------------------###

  def onInit( self ):
    self.set_allparam()

###-------------------------- Search Subtitles -------------################

  def Search_Subtitles( self ):
    self.subtitles_list = []
    self.getControl( SUBTITLES_LIST ).reset()
    self.getControl( LOADING_IMAGE ).setImage( xbmc.translatePath( os.path.join( SERVICE_DIR, self.service, "logo.png") ) )

    exec ( "from services.%s import service as Service" % (self.service))
    self.Service = Service
    self.getControl( STATUS_LABEL ).setLabel( _( 646 ) )
    msg = ""
    socket.setdefaulttimeout(float(__settings__.getSetting( "timeout" )))
    try: 
      self.subtitles_list, self.session_id, msg = self.Service.search_subtitles( self.file_original_path, self.title, self.tvshow, self.year, self.season, self.episode, self.set_temp, self.rar, self.language_1, self.language_2, self.language_3, self.stack )
    except socket.error:
      errno, errstr = sys.exc_info()[:2]
      if errno == socket.timeout:
        msg = _( 656 )
      else:
        msg =  "%s: %s" % ( _( 653 ),str(errstr[1]), )
    except:
      errno, errstr = sys.exc_info()[:2]
      msg = "Error: %s" % ( str(errstr), )

    socket.setdefaulttimeout(None)

    self.getControl( STATUS_LABEL ).setLabel( _( 642 ) % ( "...", ) )

    if not self.subtitles_list:
      xbmc.sleep(1500)
      if ((__settings__.getSetting( "search_next" )== "true") and (len(self.next) > 1)):
        self.next.remove(self.service)
        self.service = self.next[0]
        log( __name__ ,"Auto Searching '%s' Service" % (self.service,) )
        self.Search_Subtitles()
      else:
        self.next = list(self.service_list)
        if msg != "":
          self.getControl( STATUS_LABEL ).setLabel( msg )
        else:
          self.getControl( STATUS_LABEL ).setLabel( _( 657 ) )
        if self.newWindow:  
          self.setFocusId( SERVICES_LIST )
          self.getControl( SERVICES_LIST ).selectItem( 0 )
        else:
          self.list_services()
          self.setFocusId( SUBTITLES_LIST )
          self.getControl( SUBTITLES_LIST ).selectItem( 0 )  
    else:
      if not self.newWindow: self.list_services()
      subscounter = 0
      itemCount = 0
      for item in self.subtitles_list:
        if self.autoDownload and item["sync"] and  (item["language_name"] == twotofull(toOpenSubtitles_two(self.language_1))):
          self.Download_Subtitles(itemCount, True)
          __settings__.setSetting("auto_download_file", os.path.basename( self.file_original_path ))
          break
        else:
          listitem = xbmcgui.ListItem( label=item["language_name"], label2=item["filename"], iconImage=item["rating"], thumbnailImage=item["language_flag"] )
          if item["sync"]:
            listitem.setProperty( "sync", "true" )
          else:
            listitem.setProperty( "sync", "false" )
          self.list.append(subscounter)
          subscounter = subscounter + 1                                    
          self.getControl( SUBTITLES_LIST ).addItem( listitem )
        itemCount += 1
      
      self.getControl( STATUS_LABEL ).setLabel( '%i %s '"' %s '"'' % (len ( self.subtitles_list ), _( 744 ), self.file_name,) ) 
      self.setFocusId( SUBTITLES_LIST )
      self.getControl( SUBTITLES_LIST ).selectItem( 0 )
      
###-------------------------- Download Subtitles  -------------################

  def Download_Subtitles( self, pos, auto = False ):
    if auto:
      self.getControl( STATUS_LABEL ).setLabel(  _( 763 ) )
    else:
      self.getControl( STATUS_LABEL ).setLabel(  _( 649 ) )
    zip_subs = os.path.join( self.tmp_sub_dir, "zipsubs.zip")
    zipped, language, file = self.Service.download_subtitles(self.subtitles_list, pos, zip_subs, self.tmp_sub_dir, self.sub_folder,self.session_id)
    sub_lang = str(toOpenSubtitles_two(language))

    if zipped :
      self.Extract_Subtitles(zip_subs,sub_lang)
    else:
      sub_ext  = os.path.splitext( file )[1]
      sub_name = os.path.splitext( os.path.basename( self.file_original_path ) )[0]
      if (__settings__.getSetting( "lang_to_end" ) == "true"):
        file_name = "%s.%s%s" % ( sub_name, sub_lang, sub_ext )
      else:
        file_name = "%s%s" % ( sub_name, sub_ext )
      file_from = file.replace('\\','/')
      file_to = os.path.join(self.sub_folder, file_name).replace('\\','/')
      # Create a files list of from-to tuples so that multiple files may be
      # copied (sub+idx etc')
      files_list = [(file_from,file_to)]
      # If the subtitle's extension sub, check if an idx file exists and if so
      # add it to the list
      if ((sub_ext == ".sub") and (os.path.exists(file[:-3]+"idx"))):
          log( __name__ ,"found .sub+.idx pair %s + %s" % (file_from,file_from[:-3]+"idx"))
          files_list.append((file_from[:-3]+"idx",file_to[:-3]+"idx"))
      for cur_file_from, cur_file_to in files_list:
         subtitle_set,file_path  = self.copy_files( cur_file_from, cur_file_to )  
      # Choose the last pair in the list, second item (destination file)
      if subtitle_set:
        xbmc.Player().setSubtitles(files_list[-1][1])
        self.rem_files(self.tmp_sub_dir)
        self.exit_script()
      else:
        self.getControl( STATUS_LABEL ).setLabel( _( 654 ) )
        if self.newWindow:  
          self.setFocusId( SERVICES_LIST )
          self.getControl( SERVICES_LIST ).selectItem( 0 )
        else:
          self.list_services()           
          self.setFocusId( SUBTITLES_LIST )
          self.getControl( SUBTITLES_LIST ).selectItem( 0 )  

###-------------------------- Extract, Rename & Activate Subtitles  -------------################    

  def Extract_Subtitles( self, zip_subs, subtitle_lang ):
    xbmc.executebuiltin('XBMC.Extract("%s","%s")' % (zip_subs,self.tmp_sub_dir,))
    xbmc.sleep(1000)
    files = os.listdir(self.tmp_sub_dir)
    sub_filename = os.path.basename( self.file_original_path )
    exts = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass" ]
    subtitle_set = False
    if len(files) < 1 :
      self.getControl( STATUS_LABEL ).setLabel( _( 654 ) )
      if self.newWindow:  
        self.setFocusId( SERVICES_LIST )
        self.getControl( SERVICES_LIST ).selectItem( 0 )
      else:
        self.list_services()
    else :    
      self.getControl( STATUS_LABEL ).setLabel(  _( 652 ) )
      subtitle_set = False
      movie_sub = False
      episode = 0
      for zip_entry in files:
        if os.path.splitext( zip_entry )[1] in exts:
          subtitle_file, file_path = self.create_name(zip_entry,sub_filename,subtitle_lang)
          if len(self.tvshow) > 0:
            title, season, episode = regex_tvshow(False, zip_entry)
            if not episode : episode = -1
          else:
            if os.path.splitext( zip_entry )[1] in exts:
              movie_sub = True
          if ( movie_sub or len(files) < 2 or int(episode) == int(self.episode) ):
            if self.stack:
              try:
                if (re.split("(?x)(?i)\CD(\d)", zip_entry)[1]) == (re.split("(?x)(?i)\CD(\d)", sub_filename)[1]):
                  subtitle_file, file_path = self.create_name(zip_entry,sub_filename,subtitle_lang)          
                elif (re.split("(?x)(?i)\CD(\d)", zip_entry)[1]) == (re.split("(?x)(?i)\CD(\d)", self.stackSecond)[1]):
                  subtitle_file, file_path = self.create_name(zip_entry,self.stackSecond,subtitle_lang)                
                subtitle_set,file_path = self.copy_files( subtitle_file, file_path ) 
                if re.split("(?x)(?i)\CD(\d)", zip_entry)[1] == "1":
                  subToActivate = file_path
              except:
                subtitle_set = False              
            else:            
              subtitle_set,subToActivate = self.copy_files( subtitle_file, file_path )

      if not subtitle_set:
        for zip_entry in files:
          if os.path.splitext( zip_entry )[1] in exts:
            subtitle_file, file_path = self.create_name(zip_entry,sub_filename,subtitle_lang)
            subtitle_set,subToActivate  = self.copy_files( subtitle_file, file_path )

    if subtitle_set :
      xbmc.Player().setSubtitles(subToActivate)
      self.exit_script()
    else:
      self.getControl( STATUS_LABEL ).setLabel( _( 654 ) )
      if self.newWindow:  
        self.setFocusId( SERVICES_LIST )
        self.getControl( SERVICES_LIST ).selectItem( 0 )
      else:
        self.list_services()           
        self.setFocusId( SUBTITLES_LIST )
        self.getControl( SUBTITLES_LIST ).selectItem( 0 )                       

###-------------------------- Create name  -------------################

  def create_name(self,zip_entry,sub_filename,subtitle_lang):
    sub_ext  = os.path.splitext( zip_entry )[1]
    sub_name = os.path.splitext( sub_filename )[0]
    if (__settings__.getSetting( "lang_to_end" ) == "true"):
      file_name = "%s.%s%s" % ( sub_name, subtitle_lang, sub_ext )
    else:
      file_name = "%s%s" % ( sub_name, sub_ext )  
    file_path = os.path.join(self.sub_folder, file_name)
    subtitle_file = os.path.join(self.tmp_sub_dir, zip_entry)
    return subtitle_file, file_path

###-------------------------- Copy files  -------------################

  def copy_files( self, subtitle_file, file_path ):
    subtitle_set = False
    try:
      if VFS:
        xbmcvfs.copy(subtitle_file, file_path)
        log( __name__ ,"vfs module copy %s -> %s" % (subtitle_file, file_path))
      else:  
        shutil.copy(subtitle_file, file_path)
      subtitle_set = True
    except :
      import filecmp
      try:
        if filecmp.cmp(subtitle_file, file_path):
          subtitle_set = True
      except:
        dialog = xbmcgui.Dialog()
        selected = dialog.yesno( __scriptname__ , _( 748 ), _( 750 ),"" )
        if selected == 1:
          file_path = subtitle_file
          subtitle_set = True

    return subtitle_set, file_path

###-------------------------- List Available Services  -------------################

  def list_services( self ):
    self.list = []
    if self.newWindow:
      self.getControl( SERVICES_LIST ).reset()
      for serv in self.service_list:
        listitem = xbmcgui.ListItem( serv )
        self.list.append(serv)
        listitem.setProperty( "man", "false" )
        self.getControl( SERVICES_LIST ).addItem( listitem )

      if self.mansearch :
          listitem = xbmcgui.ListItem( _( 612 ) )
          listitem.setProperty( "man", "true" )
          self.list.append("Man")
          self.getControl( SERVICES_LIST ).addItem( listitem )

      if self.parsearch :
          listitem = xbmcgui.ListItem( _( 747 ) )
          listitem.setProperty( "man", "true" )
          self.list.append("Par")
          self.getControl( SERVICES_LIST ).addItem( listitem )
        
      listitem = xbmcgui.ListItem( _( 762 ) )
      listitem.setProperty( "man", "true" )
      self.list.append("Set")
      self.getControl( SERVICES_LIST ).addItem( listitem )
              
    else:
        self.getControl( SUBTITLES_LIST ).reset()
        label = ""
        for serv in self.service_list:
            if serv != self.service:
              label2 = "[COLOR=FF0084ff]%s%s[/COLOR]" %(_( 610 ), serv,)
              listitem = xbmcgui.ListItem( label,label2 )
              self.list.append(serv)
              self.getControl( SUBTITLES_LIST ).addItem( listitem )

        if self.mansearch :
            label2 = "[COLOR=FF00FF00]%s[/COLOR]" % ( _( 612 ) )
            listitem = xbmcgui.ListItem( label,label2 )
            self.list.append("Man")
            self.getControl( SUBTITLES_LIST ).addItem( listitem )

        if self.parsearch :
            label2 = "[COLOR=FF00FF00]%s[/COLOR]" % ( _( 747 ) )
            listitem = xbmcgui.ListItem( label,label2 )
            self.list.append("Par")
            self.getControl( SUBTITLES_LIST ).addItem( listitem )   

###-------------------------- Manual search Keyboard  -------------################


  def keyboard(self, parent):
    dir, self.year = xbmc.getCleanMovieTitle(os.path.split(os.path.split(self.file_original_path)[0])[1])
    if self.rar:
      tmp_dir = os.path.split(os.path.split(os.path.split(self.file_original_path)[0])[0])[1]
      dir, self.year = xbmc.getCleanMovieTitle( tmp_dir )
    if not parent:
      kb = xbmc.Keyboard("%s ()" % (dir,), _( 751 ), False)
      text = self.file_name
      kb.doModal()
      if (kb.isConfirmed()): text, self.year = xbmc.getCleanMovieTitle(kb.getText())
      self.title = text
    else:
      self.title = dir   

    log( __name__ ,"Manual/Keyboard Entry: Title:[%s], Year: [%s]" % (self.title, self.year,))
    if self.year != "" :
      self.file_name = "%s (%s)" % (self.file_name, str(self.year),)
    else:
      self.file_name = self.title   
    self.tvshow = ""
    self.next = list(self.service_list)
    self.Search_Subtitles()

###-------------------------- Exit script  -------------################


  def exit_script( self, restart=False ):
    self.close()

###-------------------------- Click  -------------################

  def onClick( self, controlId ):
    if controlId == 120:
      if self.newWindow:
        self.Download_Subtitles( self.getControl( SUBTITLES_LIST ).getSelectedPosition() )
      else:
        selection = str(self.list[self.getControl( SUBTITLES_LIST ).getSelectedPosition()])
        log( __name__ ,"In 'On click' selected : [%s]" % (selection, ) )
        if selection.isdigit():
          log( __name__ , "Selected : [%s]" % (selection, ) )
          self.Download_Subtitles( int(selection) )
        else:
          if selection == "Man":
            self.keyboard(False)
          elif selection == "Par":
            self.keyboard(True)
          else:
            self.service = selection
            self.next = list(self.service_list)
            self.Search_Subtitles()

    elif controlId == 150:
      selection = str(self.list[self.getControl( SERVICES_LIST ).getSelectedPosition()])
      log( __name__ ,"In 'On click' selected : [%s]" % (selection, )  )
      self.setFocusId( 120 )
      if selection == "Man":
        self.keyboard(False)
      elif selection == "Par":
        self.keyboard(True)
      elif selection == "Set":
        __settings__.openSettings()
        self.set_allparam()         
      else:
        self.service = selection
        self.Search_Subtitles()
                                                                                                               

###-------------------------- Remove temp files  -------------################        

  def rem_files( self, directory):
    try:
      for root, dirs, files in os.walk(directory, topdown=False):
        for items in dirs:
          shutil.rmtree(os.path.join(root, items), ignore_errors=True, onerror=None)
        for name in files:
          os.remove(os.path.join(root, name))
    except:
      try:
        for root, dirs, files in os.walk(directory, topdown=False):
          for items in dirs:
            shutil.rmtree(os.path.join(root, items).decode("utf-8"), ignore_errors=True, onerror=None)
          for name in files:
            os.remove(os.path.join(root, name).decode("utf-8"))
      except:
        pass 


###-------------------------- On Focus  -------------################

  def onFocus( self, controlId ):
    self.controlId = controlId
    try:
      if controlId == 8999:
        self.setFocusId( 150 )
    except:
      pass

###-------------------------- "Esc" , "Back" button  -------------################

  def onAction( self, action ):
    if ( action.getId() in CANCEL_DIALOG):
      self.exit_script()


