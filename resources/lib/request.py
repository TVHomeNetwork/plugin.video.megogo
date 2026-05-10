import hashlib
import requests
import time

import xbmc

class Request:
    def __init__(self, access_token, device_id, drm_support, language):
        self.access_token = access_token
        self.device_id = device_id
        self.drm_support = drm_support
        self.language = language

        self.base_api_url = 'https://api.megogo.net/v1/{}'
        self.headers = {
            'x-client-type' : 'Android',
            'x-client-version' : '5.6.3',
            'user-agent' : 'Dalvik/2.1.0 (Linux; U; Android 14; Unknown sdk_google_atv_x86; Build/UMOD.251113.003)',
            'device-name' : 'Unknown sdk_google_atv_x86',
            'device-model' : 'sdk_google_atv_x86',
            'accept-encoding' : 'gzip'
        }

        self.api_keys = {
            True : [ 'b31b4b84c7' , '_android_drm_22' ],
            False : [ '175664ecff' , '_android_22']
        }

        self.error = None
        self.recoverable = True
        self.url = None

    def send(self, url, params={}, data=None, json=True, ret=True, ret_json=True):
        result = None
        self.error = None
        self.recoverable = True
        self.url = url
        try:
            if data is None:
                response = requests.get(url, headers=self.headers, params=params)
            elif json:
                response = requests.post(url, json=data, headers=self.headers, params=params)
            else:
                response = requests.post(url, data=data, headers=self.headers, params=params)
            if ret:
                if response.status_code == 200:
                    result = response.json() if ret_json else response.text
                else:
                    try:
                        result = response.json()
                    except:
                        result = response.text
                    self.error = 'An unexpected status code of response - %s' % response.status_code
                    self.recoverable = False
            else:
                if response.status_code == 204:
                    result = True
                else:
                    try:
                        result = response.json()
                    except:
                        result = response.text
                    self.error = 'An unexpected status code of response - %s' % response.status_code
                    self.recoverable = False
            if len(response.history) > 0:
                self.url = response.history[0].headers['Location']
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.error = str(e)
        except requests.exceptions.HTTPError as e:
            self.error = str(e)
            if e.response.status_code not in [500, 502, 503, 504]:
                self.recoverable = False
        except Exception as e:
            self.error = str(e)
            self.recoverable = False
        finally:
            return result

    def send_api(self, url, params=None, data=None, json=True, ret=True, ret_json=True):
        params_dict = data if params is None else params
        if self.access_token and 'auth/refresh' not in url:
            params_dict['access_token'] = self.access_token

        if self.language:
            params_dict['lang'] = self.language

        if params_dict is not None:
            params_str = ''.join(f'{key}={value}' for key, value in params_dict.items())
            private_key = self.api_keys[self.drm_support][0]
            public_key = self.api_keys[self.drm_support][1]
            md5hex = hashlib.md5((params_str + private_key).encode('utf-8')).hexdigest()
            params_dict['sign'] = md5hex + public_key

        return self.send(url, params, data, json, ret, ret_json)

# Post requests
    def get_auth_email(self, login, action, password=None):
        url = self.base_api_url.format('auth/email')
        data = {}
        data['login'] = login
        data['action'] = action
        if password:
            data['password'] = password
        data['remember'] = '1'
        data['did'] = self.device_id
        result = self.send_api(url, params=None, data=data, json=False)
        if self.error:
            xbmc.log("MegogoRequest exception in get_auth_email: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_auth_phone(self, phone, action, code=None, send_again=False):
        url = self.base_api_url.format('auth/phone')
        data = {}
        data['login'] = phone
        data['action'] = action
        if code:
            data['verification_code'] = code
        data['remember'] = '1'
        if code is None:
            data['send_new_verification_code'] = str(send_again).lower()
        data['did'] = self.device_id
        result = self.send_api(url, params=None, data=data, json=False)
        if self.error:
            xbmc.log("MegogoRequest exception in get_auth_phone: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_tracker_init(self, access_key, geo_zone):
        url = 'http://et.megogo.net/v5/tracker/init/' + access_key
        data = {
            "additional" : {
                "device_data" : "ro.product.model=sdk_google_atv_x86,ro.product.manufacturer=unknown,ro.product.name=sdk_google_atv_x86,ro.product.brand=google,ro.product.device=generic_x86"
            },
            "configuration" : {
                "app_language" : self.language,
                "show_score" : True,
                "tv_autostart" : False,
                "video_autoplay" : True,
                "video_autoplay_sound" : True
            },
            "device" : {
                "app_geo" : geo_zone,
                "app_version" : "5.6.3",
                "connection_type" : "wi-fi",
                "model" : "sdk_google_atv_x86",
                "os_name" : "android",
                "os_version" : "14.0.0",
                "screen_height" : 1080,
                "screen_width" : 1920,
                "support_hdr" : False,
                "support_uhd" : True,
                "system_language" : self.language,
                "vendor" : "unknown"
            },
            "event_created_client_ts" : int(time.time()*1000),
            "is_subscriber" : 0,
            "platform_type" : "android"
        }
        result = self.send(url, params=None, data=data, ret_json=False)
        if self.error:
            xbmc.log("MegogoRequest exception in get_tracker_init: " + self.error, xbmc.LOGERROR)
            return False
        return result

    def get_tracker_page_view(self, access_key, page_code="page_main"):
        url = 'http://et.megogo.net/v5/tracker/page_view/' + access_key
        data = {
            "event_created_client_ts" : int(time.time()*1000),
            "page" : {
                "code" : page_code,
            }
        }
        result = self.send(url, params=None, data=data, ret_json=False)
        if self.error:
            xbmc.log("MegogoRequest exception in get_tracker_page_view: " + self.error, xbmc.LOGERROR)
            return False
        return result

# Get requests
    def get_config(self):
        url = self.base_api_url.format('configuration')
        result = self.send_api(url, params={})
        if self.error:
            xbmc.log("MegogoRequest exception in get_config: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_anon_user_token(self):
        url = self.base_api_url.format('anon/user_token')
        params = { 'did' : self.device_id }
        result = self.send_api(url, params=params)
        if self.error:
            xbmc.log("MegogoRequest exception in get_anon_user_token: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_device_code(self, device_name):
        url = self.base_api_url.format('device/code')
        params = {
            'device_name' : device_name,
            'did' : self.device_id
        }
        result = self.send_api(url, params=params)
        if self.error:
            xbmc.log("MegogoRequest exception in get_device_code: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_auth_user(self):
        url = self.base_api_url.format('auth/user')
        params = { 'did' : self.device_id }
        result = self.send_api(url, params=params)
        if self.error:
            xbmc.log("MegogoRequest exception in get_auth_user: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_auth_logout(self):
        url = self.base_api_url.format('auth/logout')
        params = { 'did' : self.device_id }
        result = self.send_api(url, params=params)
        if self.error:
            xbmc.log("MegogoRequest exception in get_auth_logout: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_auth_refresh(self, remember_me_token):
        url = self.base_api_url.format('auth/refresh')
        params = {
            'rememberme_token' : remember_me_token,
            'did' : self.device_id
        }
        result = self.send_api(url, params=params)
        if self.error:
            xbmc.log("MegogoRequest exception in get_auth_refresh: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_tv_channels(self):
        url = self.base_api_url.format('tv/channels')
        result = self.send_api(url, params={})
        if self.error:
            xbmc.log("MegogoRequest exception in get_tv_channels: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_tv_channels_grouped(self):
        url = self.base_api_url.format('tv/channels/grouped')
        result = self.send_api(url, params={})
        if self.error:
            xbmc.log("MegogoRequest exception in get_tv_channels_grouped: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_epg(self, channel_id, _from, to):
        url = self.base_api_url.format('epg')
        params = {
            'channel_id' : channel_id,
            'from' : _from,
            'to' : to
        }
        result = self.send_api(url, params=params)
        if self.error:
            xbmc.log("MegogoRequest exception in get_epg: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_stream(self, video_id, object_id):
        url = self.base_api_url.format('stream')
        params = {
            'video_id' : video_id,
            'did' : self.device_id
        }
        if object_id:
            params['object_id'] = object_id
        result = self.send_api(url, params=params)
        if self.error:
            xbmc.log("MegogoRequest exception in get_stream: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_stream_virtual(self, video_id, virtual_id):
        url = self.base_api_url.format('stream/virtual')
        params = {
            'video_id' : video_id,
            'virtual_id' : virtual_id
        }
        result = self.send_api(url, params=params)
        if self.error:
            xbmc.log("MegogoRequest exception in get_stream_virtual: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_featured_group_extended(self, group_id, category_id, object_types):
        url = self.base_api_url.format('featured/group/extended')
        params = {
            'group_id' : group_id,
            'required' : '1',
            'promo_category_id' : category_id,
            'req_feat_size' : '1',
            'object_types' : object_types,
            'video_limit' : '100',
            'vod' : 'subscription,free,single',
            'paging_strategy' : 'token'
        }
        result = self.send_api(url, params=params)
        if self.error:
            xbmc.log("MegogoRequest exception in get_featured_group_extended: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_featured_content(self, scid, object_types, page):
        url = self.base_api_url.format('featured/content')
        params = {
            'limit' : '100',
            'vod' : 'subscription,free,single',
            'object_types' : object_types,
            'id' : scid,
            'paging_strategy' : 'token',
            'page' : page
        }
        result = self.send_api(url, params=params)
        if self.error:
            xbmc.log("MegogoRequest exception in get_featured_content: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_catalog_objects(self, category_id, filters, page=None):
        url = self.base_api_url.format('catalog/objects')
        params = {
            'sort' : 'popular',
            'category_id' : category_id
        }
        for _filter in filters:
            params[_filter] = filters[_filter]['val']
        if page:
            params['page'] = page
        result = self.send_api(url, params=params)
        if self.error:
            xbmc.log("MegogoRequest exception in get_catalog_objects: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_catalog_filters(self):
        url = self.base_api_url.format('catalog/filters')
        params = { 'show_title' : 'true' }
        result = self.send_api(url, params=params)
        if self.error:
            xbmc.log("MegogoRequest exception in get_catalog_filters: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_video_info(self, video_id):
        url = self.base_api_url.format('video/info')
        params = { 'id' : video_id }
        result = self.send_api(url, params=params)
        if self.error:
            xbmc.log("MegogoRequest exception in get_video_info: " + self.error, xbmc.LOGERROR)
            return {}
        return result

    def get_search_extended(self, query, group_id=None, page=None):
        url = self.base_api_url.format('search/extended')
        params = {
            'text' : query,
            'paging_strategy':'token'
        }
        if group_id:
            params['group_id'] = group_id
        if page:
            params['page'] = page
        result = self.send_api(url, params=params)
        if self.error:
            xbmc.log("MegogoRequest exception in get_search_extended: " + self.error, xbmc.LOGERROR)
            return {}
        return result
