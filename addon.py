# -*- coding: utf-8 -*-
import os
import sys

import requests
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import re
import base64
import json
import random
import time
import datetime
from html import unescape
from urllib.parse import urlencode, quote_plus, quote, unquote, parse_qsl
import hashlib

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
params = dict(parse_qsl(sys.argv[2][1:]))
addon = xbmcaddon.Addon(id='plugin.video.megogo_atv')
PATH=addon.getAddonInfo('path')
PATH_profile=xbmcvfs.translatePath(addon.getAddonInfo('profile'))
if not xbmcvfs.exists(PATH_profile):
    xbmcvfs.mkdir(PATH_profile)
img_empty=PATH+'/resources/img/empty.png'
img_addon=PATH+'/icon.png'
fanart=PATH+'/resources/img/fanart.jpg'

UA='Dalvik/2.1.0 (Linux; U; Android 8.0.0; Unknown sdk_google_atv_x86; Build/OSR1.180418.025)'
#baseurl='http://smarttv.megogo.net/'
apiURL='https://api.megogo.net/v1/'#'https://api.megogo.net/stv/'
lang=addon.getSetting('lng')#'pl'

apis={ #apk atv ver 2.11.6
    'true':['a3a854fdd3','_android_tv_drm_4k_17'],
    'false':['2901c3d95c','_android_tv_4k_17']
}

hea={
    'x-client-type':'AndroidTV',
    'x-client-version':'2.11.6',
    'user-agent':UA,
    'device-name':'Unknown sdk_google_atv_x86',
    'device-model':'sdk_google_atv_x86',
    'accept-encoding':'gzip'
}

def translate(text):
      return addon.getLocalizedString(text)

def getCookies():
    cookies={}
    if addon.getSetting('logged')=='true':
        cookies={
            'access_token':addon.getSetting('access_token'),
            'rememberme_token':addon.getSetting('remember_me_token')
        }
    return cookies

def openF(u):
    try:
        f=open(u,'r',encoding = 'utf-8')
    except:
        f=open(u,'w+',encoding = 'utf-8')
    cont=f.read()
    f.close()
    return cont
    
def saveF(u,t):
    with open(u, 'w', encoding='utf-8') as f:
        f.write(t)

def code_gen(x,only_digit=False):
    base='0123456789abcdef' if not only_digit else '0123456789'
    count=15 if not only_digit else 9
    code=''
    for i in range(0,x):
        code+=base[random.randint(0,count)]
    return code

def getSign(p):
    isDRM=addon.getSetting('drmSupport')
    s=''.join([k+'='+p[k] for k in p.keys()])
    s+=apis[isDRM][0] #private_key
    sHash=hashlib.md5(s.encode('utf-8')).hexdigest()
    sHash+=apis[isDRM][1] #public_key
    return sHash
    

def build_url(query):
    return base_url + '?' + urlencode(query)

def addItemList(url, name, setArt, medType=False, infoLab={}, isF=True, isPla='false', contMenu=False, cmItems=[]):
    li=xbmcgui.ListItem(name)
    li.setProperty("IsPlayable", isPla)
    if medType:
        kodiVer=xbmc.getInfoLabel('System.BuildVersion')
        if kodiVer.startswith('19.'):
            li.setInfo(type=medType, infoLabels=infoLab)
        else:
            types={'video':'getVideoInfoTag','music':'getMusicInfoTag'}
            if medType!=False:
                setMedType=getattr(li,types[medType])
                vi=setMedType()
            
                labels={
                    'year':'setYear', #int
                    'episode':'setEpisode', #int
                    'season':'setSeason', #int
                    'rating':'setRating', #float
                    'mpaa':'setMpaa',
                    'plot':'setPlot',
                    'plotoutline':'setPlotOutline',
                    'title':'setTitle',
                    'originaltitle':'setOriginalTitle',
                    'sorttitle':'setSortTitle',
                    'genre':'setGenres', #list
                    'country':'setCountries', #list
                    'director':'setDirectors', #list
                    'studio':'setStudios', #list
                    'writer':'setWriters',#list
                    'duration':'setDuration', #int (in sec)
                    'tag':'setTags', #list
                    'trailer':'setTrailer', #str (path)
                    'mediatype':'setMediaType',
                    'cast':'setCast', #list        
                }
                
                if 'cast' in infoLab:
                    if infoLab['cast']!=None:
                        cast=[xbmc.Actor(c) for c in infoLab['cast']]
                        infoLab['cast']=cast
                
                for i in list(infoLab):
                    if i in list(labels):
                        setLab=getattr(vi,labels[i])
                        setLab(infoLab[i])
    li.setArt(setArt) 
    if contMenu:
        li.addContextMenuItems(cmItems, replaceItems=False)
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=isF) 

def configure():
    url=apiURL+'configuration'
    params={
        'lang':lang,
    }
    if addon.getSetting('logged')=='true':
        params['access_token']=addon.getSetting('access_token')
    params.update({'sign':getSign(params)})
    resp=req('get',url,hea,params,getCookies())
    saveF(PATH_profile+'conf.txt',str(resp['data']))

def logIn():
    
    url=apiURL+'anon/user_token'
    params={
        'did':addon.getSetting('did'),
        'lang':lang
    }
    params.update({'sign':getSign(params)})
    resp=requests.get(url,headers=hea,params=params).json()
    accessKey=resp['data']['extra']['access_key']
    
    url='http://et.megogo.net/v5/tracker/init/'+accessKey
    data={
        "additional": {
            "device_data": "ro.product.model=sdk_google_atv_x86,ro.product.manufacturer=unknown,ro.product.name=sdk_google_atv_x86,ro.product.brand=google,ro.product.device=generic_x86"
        },
        "configuration": {
            "app_language": lang,
            "show_score": True,
            "tv_autostart": False,
            "video_autoplay": True,
            "video_autoplay_sound": True
        },
        "device": {
            "app_geo": addon.getSetting('geoZone'),
            "app_version": "2.11.6",
            "connection_type": "wi-fi",
            "model": "sdk_google_atv_x86",
            "os_name": "android",
            "os_version": "8.0.0",
            "screen_height": 1080,
            "screen_width": 1920,
            "support_hdr": False,
            "support_uhd": True,
            "system_language": lang,
            "vendor": "unknown"
        },
        "event_created_client_ts": int(time.time()*1000),
        "is_subscriber": 0,
        "platform_type": "android_tv"
    }
    HEA={'content-type':'application/json; charset=UTF-8','connection':'Keep-Alive'}
    HEA.update(hea)
    resp=requests.post(url,headers=HEA,json=data)
    
    url='http://et.megogo.net/v5/tracker/page_view/'+accessKey
    data={
        "event_created_client_ts": int(time.time()*1000),
        "page": {
            "code": "page_main",
        }
    }
    resp=requests.post(url,headers=HEA,json=data)
    
    login_data=None
    logged=False
    
    loginMeth=addon.getSetting('loginMeth')
    if loginMeth=='via code':
        url=apiURL+'device/code'
        params={
            'device_name':'Device_'+code_gen(3,True),
            'lang':lang,
            'did':addon.getSetting('did')
        }
        params.update({'sign':getSign(params)})
        resp=requests.get(url,headers=hea,params=params).json()
        if 'result' in resp:
            if resp['result']=='ok':
                code=resp['data']['code']
                ok=xbmcgui.Dialog().ok("Login", translate(30021).format(c='[COLOR=yellow][B]%s[/B][/COLOR]'%(code)))
                if ok:
                    url=apiURL+'auth/user'
                    params={
                        'did':addon.getSetting('did'),
                        'lang':lang,    
                    }
                    params.update({'sign':getSign(params)})
                    resp=requests.get(url,headers=hea,params=params).json()
                    if 'result' in resp:
                        if resp['result']=='ok':
                            login_data=resp
                        else:
                            login_error=translate(30115)
                            xbmc.log('@@@Błąd logowania: '+str(resp), level=xbmc.LOGINFO)
                    else:
                        login_error=translate(30115)
                        xbmc.log('@@@Błąd logowania: '+str(resp), level=xbmc.LOGINFO)
                            
                else:
                    login_error=translate(30114)
                    xbmc.log('@@@Błąd logowania: Nie wciśnięto OK', level=xbmc.LOGINFO)
            else:
                login_error=translate(30113)
                xbmc.log('@@@Błąd logowania: '+str(resp), level=xbmc.LOGINFO)
        else:
            login_error=translate(30113)
            xbmc.log('@@@Błąd logowania: '+str(resp), level=xbmc.LOGINFO)
                        
    elif loginMeth=='via e-mail':
    
        login=addon.getSetting('username')
        password=addon.getSetting('password')
        
        if login!='' and password!='':

            url=apiURL+'auth/login/email'
            data={
                "login": login,
                "password": password,
                "remember":"1",
                "did": addon.getSetting('did'),
                "lang": lang
            }
            data.update({'sign':getSign(data)})
            HEA={'Content-Type':'application/x-www-form-urlencoded'}
            HEA.update(hea)
            resp=requests.post(url,headers=HEA,data=data).json()
            if 'result' in resp:
                if resp['result']=='ok':
                    login_data=resp
                else:
                    login_error=translate(30116)
                    xbmc.log('@@@Błąd logowania: '+str(resp), level=xbmc.LOGINFO)
            else:
                login_error=translate(30116)
                xbmc.log('@@@Błąd logowania: '+str(resp), level=xbmc.LOGINFO)
            
        else:
            login_error=translate(30102)
            xbmc.log('@@@Błąd logowania: brak danych logowania w ustawieniach wtyczki', level=xbmc.LOGINFO)

    if login_data!=None:
        addon.setSetting('access_token',resp['data']['user']['tokens']['access_token'])
        addon.setSetting('access_token_exp',str(resp['data']['user']['tokens']['access_token_expires_at'])) #6 godzin
        addon.setSetting('remember_me_token',resp['data']['user']['tokens']['remember_me_token'])
        addon.setSetting('access_key',resp['data']['user']['extra']['access_key'])
        addon.setSetting('user_id',str(resp['data']['user']['user_id']))
        addon.setSetting('logged','true')
        logged=True
            
    if logged:
        xbmcgui.Dialog().notification('Megogo', translate(30100), xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('Megogo', login_error, xbmcgui.NOTIFICATION_INFO)
    
def logOut():
    url=apiURL+'auth/logout'
    params={
        'lang':lang,
        'did':addon.getSetting('did')
    }
    if addon.getSetting('logged')=='true':
        params['access_token']=addon.getSetting('access_token')
    params.update({'sign':getSign(params)})
    resp=req('get',url,hea,params,getCookies())
    if 'result' in resp:
        xbmcgui.Dialog().notification('Megogo', translate(30103), xbmcgui.NOTIFICATION_INFO)
        addon.setSetting('access_token','')
        addon.setSetting('access_token_exp','')
        addon.setSetting('remember_me_token','')
        addon.setSetting('access_key','')
        addon.setSetting('logged','false')
        addon.setSetting('user_id','')
    else:
        #xbmcgui.Dialog().notification('Megogo', 'Błąd wylogowania', xbmcgui.NOTIFICATION_INFO)
        xbmc.log('@@@Błąd wylogowania: '+str(resp), level=xbmc.LOGINFO)
        paraLogOut()
        
def paraLogOut():
    xbmc.log('@@@ParaLogOut', level=xbmc.LOGINFO)
    xbmcgui.Dialog().notification('Megogo', translate(30103), xbmcgui.NOTIFICATION_INFO)
    addon.setSetting('access_token','')
    addon.setSetting('access_token_exp','')
    addon.setSetting('remember_me_token','')
    addon.setSetting('access_key','')
    addon.setSetting('user_id','')
    addon.setSetting('logged','false')
    xbmcplugin.endOfDirectory(addon_handle, cacheToDisc=False)
    xbmc.executebuiltin('Container.Update(plugin://plugin.video.megogo_atv/,replace)')

def refresh_tokens():

    url=apiURL+'auth/user_token'
    params={
        'user_id':addon.getSetting('user_id'),
        'lang':lang,
        'did':addon.getSetting('did')
    }
    params.update({'sign':getSign(params)})
    resp=requests.get(url,headers=hea,params=params).json()
    refreshed=False
    if 'result' in resp:
        if resp['result']=='ok':
            addon.setSetting('access_token',resp['data']['tokens']['access_token'])
            addon.setSetting('access_token_exp',str(resp['data']['tokens']['access_token_expires_at']))
            addon.setSetting('remember_me_token',resp['data']['tokens']['remember_me_token'])
            addon.setSetting('access_key',resp['data']['extra']['access_key'])
            refreshed=True
    if refreshed:
        xbmc.log('@@@Odświeżono tokeny', level=xbmc.LOGINFO)
        return True
    else:
        xbmc.log('@@@Błąd refresh_tokens: '+str(resp), level=xbmc.LOGINFO)
        paraLogOut()
        return False
    
def req(type,u,h,p,c,d={}):
    if addon.getSetting('logged')=='true':
        now=int(time.time())
        tokenExpTime=int(addon.getSetting('access_token_exp'))
        if tokenExpTime-now<=10*60:
            if not refresh_tokens():
                return
            else:
                c=getCookies()
                p['access_token']=addon.getSetting('access_token')
                del p['sign']
                p['sign']=getSign(p)
    
    if type=='get':
        resp=requests.get(u,headers=h,params=p,cookies=c).json()
    elif type=='post':
        resp=requests.post(u,headers=h,params=p,cookies=c,json=d).json()
    
    return resp
    
    
def main_menu():
    sources=[
        [translate(30001),'live','DefaultTVShows.png'],
        [translate(30002),'liveCategs','DefaultTVShows.png'],
        [translate(30003),'replay','DefaultYear.png'],
        [translate(30004),'vod','DefaultAddonVideo.png'],
        [translate(30005),'search','DefaultAddonsSearch.png'],
    ]
    if addon.getSetting('logged')!='true':
        sources.append([translate(30006),'logIn','DefaultUser.png'])
    else:
        sources.append([translate(30007),'logOut','DefaultUser.png'])
    for s in sources:
        setArt={'icon': s[2],'fanart':fanart}
        url = build_url({'mode':s[1],'page':'0'})       
        addItemList(url, s[0], setArt)
    xbmcplugin.endOfDirectory(addon_handle)

def channels(groups=False): #helper
    url=apiURL+'tv/channels' if not groups else apiURL+'tv/channels/grouped'
    params={
        'lang':lang,
    }
    if addon.getSetting('logged')=='true':
        params['access_token']=addon.getSetting('access_token')
    params.update({'sign':getSign(params)})
    resp=req('get',url,hea,params,getCookies())
    if 'result' in resp:
        chans=resp['data']['channels'] if not groups else resp['data']['channel_groups']
    else:
        chans=[]
    return chans
    
def liveCategs():
    groups=channels(True)
    for r in groups:
        name=r['type_name']
        gid=str(r['type_id'])
        
        setArt={'icon': 'DefaultTVShows.png','fanart':fanart}
        URL=build_url({'mode':'tvList','gid':gid})
        addItemList(URL, name, setArt)
        
    xbmcplugin.endOfDirectory(addon_handle)

def tvList(type,gid=None):
    if gid==None:
        chans=channels()
    else:
        chansData=channels(True)
        chans=[g['objects'] for g in chansData if g['type_id']==int(gid)][0]
    
    if type=='live':
        chanIDs=','.join([str(c['id']) for c in chans])
        epg=epgLive(chanIDs)
            
    for c in chans:
        img=c['image']['original']
        title=c['title']
        cid=str(c['id'])
        
        if type=='live':
            isFolder=False
            isPlayable='true'
            URL=build_url({'mode':'playSource','cid':str(c['id'])})
            show=True if c['vod_channel']==False and c['is_available'] else False
            plot=epg[cid]
            
        elif type=='replay':
            isFolder=True
            isPlayable='false'
            URL=build_url({'mode':'calendar','cid':str(c['id'])})
            show=True if (c['is_dvr'] or c['vod_channel']) and c['is_available'] else False
            plot=''
                
        setArt={'thumb': img, 'poster': img, 'banner': img, 'icon': img, 'fanart': img}
        iL={'title': title,'sorttitle': title,'plot': plot}
        if show:
            addItemList(URL, title, setArt, 'video', iL, isFolder, isPlayable)
    
    xbmcplugin.addSortMethod(handle=addon_handle,sortMethod=xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.addSortMethod(handle=addon_handle,sortMethod=xbmcplugin.SORT_METHOD_TITLE)
    xbmcplugin.endOfDirectory(addon_handle)

def calendar(cid):
    days=7
    now=datetime.datetime.now()
    for i in range(0,days+1):
        date=(now-datetime.timedelta(days=i*1)).strftime('%Y-%m-%d')
       
        setArt={'icon': 'DefaultYear.png','fanart':fanart}
        url=build_url({'mode':'programList','cid':cid,'date':date})
        addItemList(url, date, setArt)
        
    xbmcplugin.endOfDirectory(addon_handle)

def getEPG(cid,ts,te):
    url=apiURL+'epg'
    params={
        'channel_id':cid,
        'from':ts,
        'to':te,
        'lang':lang,
    }
    if addon.getSetting('logged')=='true':
        params['access_token']=addon.getSetting('access_token')
    params.update({'sign':getSign(params)})
    resp=req('get',url,hea,params,getCookies())
    progs=resp['data'][0]['programs']
    return progs
    
def epgLive(c):
    since=int(time.time())
    till=since+8*60*60
    url=apiURL+'epg'
    params={
        'channel_id':c,
        'from':str(since),
        'to':str(till),
        'lang':lang,
    }
    if addon.getSetting('logged')=='true':
        params['access_token']=addon.getSetting('access_token')
    params.update({'sign':getSign(params)})
    resp=req('get',url,hea,params,getCookies())
    chans=resp['data']
    epg={}
    for c in chans:
        cid=str(c['id'])
        e=''
        for p in c['programs']:
            title=p['title']
            since=datetime.datetime.fromtimestamp(p['start_timestamp']).strftime('%H:%M')
            e+='[B]%s[/B] %s\n'%(since,title)
        epg[cid]=e
    return epg
    
    
def programList(cid,d):
    now=time.time()
    ts=datetime.datetime(*(time.strptime(d, "%Y-%m-%d")[0:6])).timestamp()
    if ts<now-7*24*60*60:
        ts=now-7*24*60*60
    te=(datetime.datetime(*(time.strptime(d, "%Y-%m-%d")[0:6]))+datetime.timedelta(days=1)).timestamp()
    if te>now:
        te=now
    epg=getEPG(cid,str(int(ts)),str(int(te)))
    for e in epg:
        if 'virtual_object_id' in e or 'object_id' in e:
            title=e['title']
            since=datetime.datetime.fromtimestamp(e['start_timestamp']).strftime('%H:%M')
            till=datetime.datetime.fromtimestamp(e['end_timestamp']).strftime('%H:%M')
            name='[B]%s - %s[/B] %s'%(since,till,title)
            desc=e['description'] if 'description' in e else ''
            try:
                img=e['pictures']['original']
            except:
                img=img_empty
            
            if 'virtual_object_id' in e:
                vid=e['virtual_object_id']
                url=build_url({'mode':'playReplay','vid':str(vid),'cid':cid})
            elif 'object_id' in e:
                vid=e['object_id']
                url=build_url({'mode':'playVODchan','vid':str(vid),'cid':cid})
            
            setArt={'thumb': img, 'poster': img, 'banner': img, 'icon': img, 'fanart': fanart}
            iL={'title': title,'sorttitle': title,'plot': desc}
            addItemList(url, name, setArt, 'video', iL, isF=False, isPla='true')
    
    xbmcplugin.setContent(addon_handle, 'videos')
    xbmcplugin.endOfDirectory(addon_handle)

def playSource(c,vid=None,vod=False,vodChan=False):
    if vid==None: #live channels/VOD
        url=apiURL+'stream'
        params={
            'video_id':c,
            'lang':lang,
            'did':addon.getSetting('did')
        }
    elif vodChan: #vod channels
        url=apiURL+'stream'
        params={
            'video_id':vid,
            'object_id':c,
            'lang':lang,
            'did':addon.getSetting('did')
        }   
    else: #replay
        url=apiURL+'stream/virtual'
        params={
            'video_id':c,
            'virtual_id':vid,
            'lang':lang
        }
    if addon.getSetting('logged')=='true':
        params['access_token']=addon.getSetting('access_token')
    params.update({'sign':getSign(params)})    
    resp=req('get',url,hea,params,getCookies())
    
    streamData=resp['data']
    if addon.getSetting('manualSelectedBitrate')=='false':
        #stream_url=streamData['src'] #manifest combo
        bitrates=streamData['bitrates']
        def sortFN(i):
            return i['bitrate']
        bitrates.sort(key=sortFN,reverse=True)
        stream_url=bitrates[0]['src']
        lic_url=bitrates[0]['license_server'] if 'license_server' in bitrates[0] else None
    else:
        srcsName=[b['name'] for b in streamData['bitrates']]
        srcs=[b['src'] for b in streamData['bitrates']]
        select = xbmcgui.Dialog().select(translate(30104), srcsName)
        if select > -1:
            stream_url=srcs[select]
            if 'license_server' in streamData['bitrates'][select]:
                lic_url=streamData['bitrates'][select]['license_server']
            else:
                lic_url=None
        else:
            stream_url=srcs[-1]
            if 'license_server' in streamData['bitrates'][-1]:
                lic_url=streamData['bitrates'][-1]['license_server']
            else:
                lic_url=None
           
    if addon.getSetting('audVOD')=='0' and vod and len(streamData['audio_tracks'])>0:
        audsName=[b['display_name'] for b in streamData['audio_tracks']]
        auds=[b['index'] for b in streamData['audio_tracks']]
        select = xbmcgui.Dialog().select(translate(30105), audsName)
        if select > -1:
            audID=auds[select]
        else:
            audID=auds[-1]
        aud_def_ID=[b['index'] for b in streamData['audio_tracks'] if b['is_active']==True][0]
        stream_url=stream_url.replace('/a/%s/' %(aud_def_ID),'/a/%s/' %(audID))
    
    '''
    if ts!=None:
        now=int(time.time())
        difTime=now-int(ts)
        stream_url=stream_url.replace('/type.live','/ts/'+str(difTime)+'/type.live')
    '''
    if 'stream_type' in streamData:
        protocol=streamData['stream_type']
        protocols={'dash':'mpd','hls':'hls'}
        if 'license_server' not in streamData:
            isDRM=False
        else:
            isDRM=True
            licHEA={
                'User-Agent':UA,
                'content-type':''
            }
            #licURL=streamData['license_server']+'|'+urlencode(licHEA)+'|R{SSM}|'
            #stream_url=streamData['src']
            licURL=lic_url+'|'+urlencode(licHEA)+'|R{SSM}|'
        
        if not isDRM and addon.getSetting('playerType')=='ffmpeg':
            play_item = xbmcgui.ListItem(path=stream_url)
            play_item.setProperty("IsPlayable", "true")
            xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
        else:
        
            import inputstreamhelper
            
            PROTOCOL = protocols[protocol]
            DRM = 'com.widevine.alpha'
            is_helper = inputstreamhelper.Helper(PROTOCOL,drm=DRM)
            
            if is_helper.check_inputstream():
                play_item = xbmcgui.ListItem(path=stream_url)                     
                play_item.setMimeType('application/xml+dash')
                play_item.setContentLookup(False)
                play_item.setProperty('inputstream', is_helper.inputstream_addon)        
                play_item.setProperty("IsPlayable", "true")
                play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
                play_item.setProperty('inputstream.adaptive.stream_headers', 'User-Agent='+UA)
                play_item.setProperty('inputstream.adaptive.manifest_headers', 'User-Agent='+UA)
                if isDRM:
                    play_item.setProperty('inputstream.adaptive.license_type', DRM)
                    play_item.setProperty('inputstream.adaptive.license_key', licURL)
            
            xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
    else:
        xbmcgui.Dialog().notification('Megogo', translate(30106), xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem())
    
    
def listM3U():
    file_name = addon.getSetting('fname')
    path_m3u = addon.getSetting('path_m3u')
    if file_name == '' or path_m3u == '':
        xbmcgui.Dialog().notification('Megogo', translate(30107), xbmcgui.NOTIFICATION_ERROR)
        return
    xbmcgui.Dialog().notification('Megogo', translate(30108), xbmcgui.NOTIFICATION_INFO)
    chans=channels()
    data = '#EXTM3U\n'
    for c in chans:
        if c['vod_channel']==False:
            img=c['image']['original']
            chName=c['title']
            cid=str(c['id'])
            if c['is_dvr']:
                data += '#EXTINF:0 tvg-id="%s" tvg-logo="%s" group-title="Megogo" catchup="append" catchup-source="&s={utc:Y-m-dTH:M:S}&e={utcend:Y-m-dTH:M:S}" catchup-days="7",%s\nplugin://plugin.video.megogo_atv?mode=playSource&cid=%s\n' %(chName,img,chName,cid)
            else:
                data += '#EXTINF:0 tvg-id="%s" tvg-logo="%s" group-title="Megogo" ,%s\nplugin://plugin.video.megogo_atv?mode=playSource&cid=%s\n' %(chName,img,chName,cid)
    
    f = xbmcvfs.File(path_m3u + file_name, 'w')
    f.write(data)
    f.close()
    xbmcgui.Dialog().notification('Megogo', translate(30109), xbmcgui.NOTIFICATION_INFO)

def playSourceSC(cid,s,e): #Simple Client catchup
    co=int(addon.getSetting('cuOffset'))
    ts=(datetime.datetime(*(time.strptime(s, "%Y-%m-%dT%H:%M:%S")[0:6]))+datetime.timedelta(hours=co-1)).timestamp()
    te=(datetime.datetime(*(time.strptime(e, "%Y-%m-%dT%H:%M:%S")[0:6]))+datetime.timedelta(hours=co+1)).timestamp()
    
    epg=getEPG(cid,str(int(ts)),str(int(te)))
    progs=[e['virtual_object_id'] for e in epg if 'virtual_object_id' in e and e['start_timestamp']==int(ts)]
    if len(progs)>0:
        playSource(cid,progs[0])
    else:
        xbmcgui.Dialog().notification('Megogo', translate(30110), xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem())

#VOD

vods={
    '16|180476': {'name':'Movies','types':'FILM,FILMSERIAL,FILM3D'},
    '4|180496': {'name':'Series','types':'SERIAL,SHOW,SHOWFILM'},
    '6|180486': {'name':'Cartoons','types':'MULTFILM,MULTSERIAL'},
    '9|0':{'name':'TV programs and shows','types':''},
    '22|0':{'name':'Sport','types':''},
}
       
def vod():
    for i in list(vods):
        setArt={'icon': 'DefaultAddonVideo.png','fanart':fanart}
        url = build_url({'mode':'vodSubcategs','categ':i})       
        addItemList(url, vods[i]['name'], setArt)
    xbmcplugin.endOfDirectory(addon_handle)
    
def vodSubcategs(categ):
    category_id,group_id=categ.split('|')
    if group_id!='0':
        url=apiURL+'featured/group/extended'
        params={
            'group_id':group_id,
            'required':'1',
            'promo_category_id':category_id,
            'req_feat_size':'1',
            'object_types':vods[categ]['types'],
            'video_limit':'100',
            'vod':'subscription,free,single',
            'paging_strategy':'token',
            'lang':lang
        }
        if addon.getSetting('logged')=='true':
            params['access_token']=addon.getSetting('access_token')
        params.update({'sign':getSign(params)})
        resp=req('get',url,hea,params,getCookies())
        saveF(PATH_profile+'vod.txt',str(resp['data']['group']['sub_featured']))
        
        for r in resp['data']['group']['sub_featured']:
            if r['content_type']=='video':
                cid=str(r['id'])
                title=r['title']
                
                setArt={'icon': 'DefaultAddonVideo.png','fanart':fanart}
                url = build_url({'mode':'vodList','scID':cid,'categ':categ})       
                addItemList(url, title, setArt)
    #katalog
    setArt={'icon': 'DefaultAddonVideo.png'}
    url = build_url({'mode':'vodList','scID':'all','categ':categ})       
    addItemList(url, '[B]%s[/B]'%(translate(30008)), setArt)
    
    xbmcplugin.endOfDirectory(addon_handle)

def getAvail(x):#helper
    data={'svod':'subscription','fvod':'free','tvod':'buy','dto':'rent','advod':'free with adv.'}
    return ', '.join([data[i] for i in x ])
    
def getLabels(x,t):#helper
    #t: video_country_filters, genres
    data=eval(openF(PATH_profile+'conf.txt'))
    result=[]
    for xx in x:
        result.append([d['title'] for d in data[t] if d['id']==xx][0])
        
    return result

def addVideoItem(v): #helper
    vid=str(v['id'])
    title=v['title']
    rating=v['rating_imdb']
    img=v['image']['original']
    countries=getLabels(v['countries'],'video_country_filters')
    genres=getLabels(v['genres'],'genres')
    try:
        year=int(v['year'])
    except:
        year=0
    dur=v['duration'] if 'duration' in v else 0
    avail=getAvail(v['delivery_rules'])
    desc='[B]Availibility: [/B]'+avail
    if dur!=0:
        isF=False
        isP='true'
        URL=build_url({'mode':'playVOD','vid':vid})
        iL={'title': title,'sorttitle': title,'mpaa':rating,'plotoutline':desc,'plot': desc,'year':year,'genre':genres,'duration':dur,'country':countries,'mediatype':'movie'}
    else:
        isF=True
        isP='false'
        URL=build_url({'mode':'seasonList','vid':vid})
        iL={'title': title,'sorttitle': title,'mpaa':rating,'plotoutline':desc,'plot': desc,'year':year,'genre':genres,'country':countries,'mediatype':'tvshow'}
    
    cmItems=[('[B]Details[/B]','RunPlugin(plugin://plugin.video.megogo_atv?mode=details&vid='+vid+')')]
    
    setArt={'thumb': img, 'poster': img, 'banner': img, 'icon': img, 'fanart':fanart}
    addItemList(URL, title, setArt, 'video', iL, isF, isP, True, cmItems)
    
def vodList(scid,categ,page):
    if scid!='all':
        if page==None:
            ex=eval(openF(PATH_profile+'vod.txt'))
            data=[d for d in ex if d['id']==int(scid)][0]
            videos=data['videos']
        else:
            url=apiURL+'featured/content'
            params={
                'limit':'100',
                'vod':'subscription,free,single',
                'object_types':vods[categ]['types'],
                'id':scid,
                'paging_strategy':'token',
                'page':page,
                'lang':lang
            }
            if addon.getSetting('logged')=='true':
                params['access_token']=addon.getSetting('access_token')
            params.update({'sign':getSign(params)})
            resp=req('get',url,hea,params,getCookies())
            data=resp['data']
            videos=data['videos']
    else: #katalogi
        addon.setSetting('lastPath',xbmc.getInfoLabel('ListItem.FileNameAndPath'))
        url=apiURL+'catalog/objects'
        params={
            'sort':'popular', #do ustawień
            'category_id':categ.split('|')[0],
            #'limit':'100',
            #'vod':'subscription,free,single',
            #'page':page,
            'lang':lang
        }
        
        #uwzględnienie filtrów
        fltrs=addon.getSetting('filters')
        if fltrs!='':
            fltrs=eval(fltrs)
            for f in list(fltrs):
                params[f]=fltrs[f]['val']
                
        if page!=None:
            params['page']=page
        if addon.getSetting('logged')=='true':
            params['access_token']=addon.getSetting('access_token')
        params.update({'sign':getSign(params)})
        resp=req('get',url,hea,params,getCookies())
        data=[g for g in resp['data']['groups'] if g['content_type']=='video']
        if len(data)>0:
            videos=data[0]['videos']
            data=data[0]
        else:
            videos=[]

        #filtry
        if page==None:            
            setArt={'thumb': '', 'poster': '', 'banner': '', 'icon': '', 'fanart':''}
            URL=build_url({'mode':'catalogFltrs'}) 
            addItemList(URL, '[B]Filtry[/B]', setArt)
            
            URL=build_url({'mode':'catalogRefresh'}) 
            addItemList(URL, '>>> List refresh <<<', setArt, isF=False)
        
    
    for v in videos:
        addVideoItem(v)

    if 'next_page' in data:
        setArt={'thumb': '', 'poster': '', 'banner': '', 'icon': img_empty, 'fanart':''}
        url = build_url({'mode':'vodList','scID':scid,'categ':categ,'page':data['next_page']})  
        addItemList(url, '[B][COLOR=cyan]>>> %s[/COLOR][/B]'%(translate(30020)), setArt)

    
    xbmcplugin.setContent(addon_handle, 'videos')
    xbmcplugin.endOfDirectory(addon_handle)

def seasonList(vid):
    url=apiURL+'video/info'
    params={
        'id':vid,
        'lang':lang
    }
    if addon.getSetting('logged')=='true':
        params['access_token']=addon.getSetting('access_token')
    params.update({'sign':getSign(params)})
    resp=req('get',url,hea,params,getCookies())
    saveF(PATH_profile+'serial.txt',str(resp['data']['season_list']))
    data=resp['data']
    img=data['image']['original']
    plot=data['description']
        
    for r in data['season_list']:
        title=r['title']
        sid=str(r['id'])
        
        iL={'plot':plot}
        setArt={'icon': img}
        url = build_url({'mode':'epList','sid':sid})       
        addItemList(url, title, setArt)

    xbmcplugin.endOfDirectory(addon_handle)
        
def epList(sid):
    data=eval(openF(PATH_profile+'serial.txt'))
    eps=[s for s in data if s['id']==int(sid)][0]
    seas=eps['order']
    title=eps['title']
    for e in eps['episode_list']:
        vid=e['id']
        ep=e['order']
        tit='Sezon %s Odc. %s'%(str(seas),str(ep))
        if e['title']!='':
            tit+=' | '+e['title']
        dur=e['duration']
        desc=e['description']
        img=e['image']
        
        iL={'title': title,'sorttitle': title,'plotoutline':desc,'plot': desc,'duration':dur,'season':seas,'episode':ep,'mediatype':'episode'}        
        setArt={'thumb': img, 'poster': img, 'banner': img, 'icon': img, 'fanart':''}
        URL=build_url({'mode':'playVOD','vid':vid})
        addItemList(URL, tit, setArt, 'video', iL, False, 'true')
        
    xbmcplugin.setContent(addon_handle, 'videos')
    xbmcplugin.endOfDirectory(addon_handle)
    
def search():
    qry=xbmcgui.Dialog().input(u'%s:'%(translate(30111)), type=xbmcgui.INPUT_ALPHANUM)
    if qry:
        url=apiURL+'search/extended'
        params={
            'text':qry,
            'paging_strategy':'token',
            'lang':lang
        }
        if addon.getSetting('logged')=='true':
            params['access_token']=addon.getSetting('access_token')
        params.update({'sign':getSign(params)})
        resp=req('get',url,hea,params,getCookies())
        saveF(PATH_profile+'search.txt',str(resp['data']))
        for r in resp['data']['group_order']:   
            if r!='person':
                groups={'TV':'TV Channels','video':'Videos','program':'On TV'}
                setArt={'poster':img_addon,'icon': 'OverlayUnwatched.png'}
                URL=build_url({'mode':'searchRes','categ':r,'query':qry})
                addItemList(URL, groups[r], setArt)
    
        xbmcplugin.endOfDirectory(addon_handle)        
            
    else:
        main_menu()

def searchRes(c,qry,page=None):
    if page==None: #1. strona
        data=eval(openF(PATH_profile+'search.txt'))['groups'][c.lower()]
    else: #kolejne strony
        data=eval(openF(PATH_profile+'conf.txt'))
        group_id=[str(g['id']) for g in data['search_groups'] if g['type']==c][0]
        
        url=apiURL+'search/extended'
        params={
            'text':qry,
            'group_id':group_id,
            'paging_strategy':'token',
            'page':page,
            'lang':lang
        }
        if addon.getSetting('logged')=='true':
            params['access_token']=addon.getSetting('access_token')
        params.update({'sign':getSign(params)})
        resp=req('get',url,hea,params,getCookies())
        data=resp['data']['groups'][c.lower()]
    
    for i in data['items']:
        if c=='video':
            addVideoItem(i)
        
        elif c=='program':
            title=i['title']
            now=int(time.time())
            avail=i['channel']['is_available']
            cid=str(i['channel']['id'])
            chName=i['channel']['title']
            date=datetime.datetime.fromtimestamp(i['start_timestamp']).strftime('%Y-%m-%d')
            since=datetime.datetime.fromtimestamp(i['start_timestamp']).strftime('%H:%M')
            till=datetime.datetime.fromtimestamp(i['end_timestamp']).strftime('%H:%M')
            col='white' if i['start_timestamp']<now and avail else 'gray'
            tit='[COLOR=%s][B]%s [/B]| %s - %s [B]%s[/B] [/COLOR]| [COLOR=yellow]%s[/COLOR]'%(col,date,since,till,title,chName)
            try:
                img=i['images']['original']
            except:
                img=img_addon
            if avail and i['start_timestamp']<now:
                isF=True
                isP='false'
                URL=build_url({'mode':'programList','cid':cid,'date':date})
            else:
                isF=False
                isP='false'
                URL=build_url({'mode':'noPlay'})
            
            setArt={'icon': img}
            addItemList(URL, tit, setArt, 'video', {}, isF, isP)
            
        elif c=='TV':
            img=i['image']['original']
            title=i['title']
            cid=str(i['id'])
            avail=True if i['vod_channel']==False and i['is_available'] else False
            
            if avail:
                isF=False
                isP='true'
                URL=build_url({'mode':'playSource','cid':cid})
                
            else:
                title='[COLOR=gray]%s[/COLOR]'%(title)
                isF=False
                isP='false'
                URL=build_url({'mode':'noPlay'})
                
            setArt={'icon': img}
            addItemList(URL, title, setArt, 'video', {}, isF, isP)
            
    if 'next_page' in data:
        setArt={'thumb': '', 'poster': '', 'banner': '', 'icon': img_empty, 'fanart':''}
        url = build_url({'mode':'searchRes','categ':c,'query':qry,'page':data['next_page']})  
        addItemList(url, '[B][COLOR=cyan]>>> %s[/COLOR][/B]'%(translate(30020)), setArt) 
    
    xbmcplugin.setContent(addon_handle, 'videos')
    xbmcplugin.endOfDirectory(addon_handle)
    

def details(vid):
    url=apiURL+'video/info'
    params={
        'id':vid,
        'lang':lang
    }
    if addon.getSetting('logged')=='true':
        params['access_token']=addon.getSetting('access_token')
    params.update({'sign':getSign(params)})
    resp=req('get',url,hea,params,getCookies())
    v=resp['data']
    
    title=v['title']
    origTitle=v['title_original']
    vidType=v['video_type']
    rating=v['rating_imdb']
    age_limit=v['age_limit']    
    #img=v['image']['original']
    countries=getLabels(v['countries'],'video_country_filters')
    countries=', '.join(countries)
    genres=getLabels(v['genres'],'genres')
    genres=', '.join(genres)
    cast=', '.join([c['name_original'] for c in v['people']])
    audio=', '.join(v['audio_list'])
    year=v['year']
    dur=v['duration'] if 'duration' in v else 0
    desc=v['description']
    
    plot='[B]%s[/B] (%s)'%(title,origTitle)+'\n'
    plot+='[COLOR=yellow][B]%s[/B][/COLOR]\n'%(vidType)
    plot+='[B]%s: [/B]%s\n'%(translate(30009),year)
    plot+='[B]%s: [/B]%s\n'%(translate(30010),countries)
    plot+='[B]%s: [/B]%s\n'%(translate(30011),genres)
    plot+='[B]%s: [/B]%s\n'%(translate(30012),cast)
    plot+='[B]%s: [/B]%s\n'%(translate(30013),age_limit)
    plot+='[B]%s: [/B]%s\n'%(translate(30014),rating)
    plot+='[B]%s: [/B]%s\n'%(translate(30015),audio)
    if dur!=0:
        plot+='[B]%s: [/B]%s min.\n'%(translate(30016),str(int(dur/60)))
    plot+='\n%s\n'%(desc)    
       
    if plot=='':
        plot=translate(30017)
    
    dialog = xbmcgui.Dialog()
    dialog.textviewer('%s:'%(translate(30018)), plot)

def catalogFltrs():
    items=[
        [translate(30019),'fltrClear']
    ]
    for i in items:
        title='<<< %s >>>'%(i[0])
        setArt={'thumb': '', 'poster': '', 'banner': '', 'icon': 'DefaultTags.png', 'fanart':''}
        url = build_url({'mode':i[1]})  
        addItemList(url, title, setArt, isF= False, isPla='false') 
    
    setFilters=addon.getSetting('filters')
    setFltrs=eval(setFilters) if setFilters!='' else {}
    
    url=apiURL+'catalog/filters'
    params={
        'lang':lang,
        'show_title':'true'
    }
    if addon.getSetting('logged')=='true':
        params['access_token']=addon.getSetting('access_token')
    params.update({'sign':getSign(params)})
    resp=req('get',url,hea,params,getCookies())
    saveF(PATH_profile+'filters.txt',str(resp['data']['filter_by']))
    for r in resp['data']['filter_by']:
        if r['id'] not in ['category_id','finger_language']:
            title=r['title']
            if r['id'] in setFltrs:
                title +=': [I]%s[/I]'%(setFltrs[r['id']]['lab'])
            
            setArt={'thumb': '', 'poster': '', 'banner': '', 'icon': 'DefaultTags.png', 'fanart':''}
            url = build_url({'mode':'fltrSet','fid':r['id']})  
            addItemList(url, title, setArt, isF= False, isPla='false') 
    
    xbmcplugin.endOfDirectory(addon_handle)

def fltrSet(fid):
    fltrs=eval(openF(PATH_profile+'filters.txt'))
    fltr=[f for f in fltrs if f['id']==fid][0]
    
    if fltr['multichoice']:
        select = xbmcgui.Dialog().multiselect('%s:'%(translate(30112)), [f['title'] for f in fltr['items']])
        if len(select)>0:
            setFilters=addon.getSetting('filters')
            setFltrs=eval(setFilters) if setFilters!='' else {}
            setFltrs[fid]={'val':','.join([fltr['items'][s]['id'] for s in select]),'lab':','.join([fltr['items'][s]['title'] for s in select])}
            addon.setSetting('filters',str(setFltrs))
            
    else:
        select = xbmcgui.Dialog().select('%s:'%(translate(30112)), [f['title'] for f in fltr['items']])
        if select > -1:
            setFilters=addon.getSetting('filters')
            setFltrs=eval(setFilters) if setFilters!='' else {}
            setFltrs[fid]={'val':fltr['items'][select]['id'],'lab':fltr['items'][select]['title']}
            addon.setSetting('filters',str(setFltrs))
            
    xbmc.executebuiltin('Container.Refresh')
    
def fltrClear():
    setFilters=addon.setSetting('filters','')
    xbmc.executebuiltin('Container.Refresh')
    
    
mode = params.get('mode', None)

if not mode:
    did=addon.getSetting('did')
    if did=='' or did==None:
        addon.setSetting('did','ANDROIDTV'+code_gen(10,True)+'__'+code_gen(16))
        addon.setSetting('adid','%s-%s-%s-%s-%s'%(code_gen(8),code_gen(4),code_gen(4),code_gen(4),code_gen(12)))
    
    now=int(time.time())
    confUpdt=addon.getSetting('confUpdt')
    if confUpdt=='':
        confUpdt='0'
    if now-int(confUpdt)>=6*60*60:
        configure()
        addon.setSetting('confUpdt',str(now))
    
    main_menu()
else:
    if mode=='live' or mode=='replay':
        tvList(mode)
    
    if mode=='tvList':
        gid=params.get('gid')
        tvList('live',gid)
    
    if mode=='liveCategs':
        liveCategs()
           
    if mode=='calendar':
        cid=params.get('cid')
        calendar(cid)
        
    if mode=='programList':
        cid=params.get('cid')
        date=params.get('date')
        programList(cid,date)
        
    if mode=='playReplay':
        cid=params.get('cid')
        vid=params.get('vid')
        playSource(cid,vid)
    
    if mode=='playSource':
        cid=params.get('cid')
        s=params.get('s')
        e=params.get('e')
        if s!=None and e!=None:
            playSourceSC(cid,s,e)
        else:
            playSource(cid)
    
    if mode=='listM3U':
        listM3U()
    
    if mode=='vod':
        vod()
     
    if mode=='vodSubcategs':
        categ=params.get('categ')
        vodSubcategs(categ)
    
    if mode=='vodList':
        scID=params.get('scID')
        page=params.get('page')
        categ=params.get('categ')
        vodList(scID,categ,page)
    
    if mode=='seasonList':
        vid=params.get('vid')
        seasonList(vid)
    
    if mode=='epList':
        sid=params.get('sid')
        epList(sid)
    
    if mode=='search':
        search()
    
    if mode=='searchRes':
        categ=params.get('categ')
        qry=params.get('query')
        page=params.get('page')
        searchRes(categ,qry,page)
    
    if mode=='noPlay':
        pass
        
    if mode=='details':
        vid=params.get('vid')
        details(vid)
    
    if mode=='playVOD':
        vid=params.get('vid')
        playSource(vid,None,True)

    if mode=='playVODchan':
        vid=params.get('vid')
        playSource(cid,vid,vodChan=True)

    if mode=='logIn':
        logIn()
        xbmcplugin.endOfDirectory(addon_handle, cacheToDisc=False)
        xbmc.executebuiltin('Container.Update(plugin://plugin.video.megogo_atv/,replace)')
            
    if mode=='logOut':
        logOut()
        if addon.getSetting('logged')=='false':
            xbmcplugin.endOfDirectory(addon_handle, cacheToDisc=False)
            xbmc.executebuiltin('Container.Update(plugin://plugin.video.megogo_atv/,replace)')
    
    if mode=='catalogFltrs':
        catalogFltrs()
        
    if mode=='fltrSet':
        fid=params.get('fid')
        fltrSet(fid)
        
    if mode=='fltrClear':
        fltrClear()
    
    if mode=='fltrApply':
        fltrApply()
            
    if mode=='catalogRefresh':
        xbmc.executebuiltin('Container.Refresh')
        