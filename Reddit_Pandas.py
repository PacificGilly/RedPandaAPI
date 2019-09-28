import os
import sys
import platform
import time
import urllib
import praw
import json
import ctypes

from pathlib import Path
from moviepy.editor import VideoFileClip
from prawcore.exceptions import ResponseException

import numpy as np

class RedditPanda:

    # Define the path for the seetings of the Windows Terminal. N.B. This 
    # path is static and would work on any windows computer.
    settings_path = os.path.expandvars('%LOCALAPPDATA%/Packages/Microsoft.' \
        'WindowsTerminal_8wekyb3d8bbwe/LocalState/profiles.json')
    image_path = "%USERPROFILE%/Pictures/Reddit_{subreddit}_{key}"
    
    def __init__(self, client_id, client_key, user_agent, base_dir=None):
        """Initalise the RedditPanda class by connecting to Reddit.

        :param client_id : str
            The client ID for a Reddit API application.
        :param client_key : str
            The client key associated with the client ID.
        :param base_dir : str, optional
            The base directory you want to use to store the list of URLs
            found for a subreddit.
        """

        # Connect to Reddit.
        self.reddit = self._reddit_login(client_id, client_key, user_agent)

        # Define base directory
        self.base_dir = base_dir if base_dir is not None else ""

    def _reddit_login(self, client_id, client_key, user_agent):
        """Logs you into reddit's api.
        """

        reddit_login = praw.Reddit(client_id=client_id,
                     client_secret=client_key,
                     user_agent=user_agent)

        # Check we are connected to Reddit correctly.
        try:
            reddit_login.random_subreddit()
        except ResponseException:
            raise ValueError("Client ID or the Client Secret is incorrect. " \
                "Can't connect to Reddit!")

        return reddit_login

    @staticmethod
    def _check_media_type(url):
        """Check the url for .gifv file format.
        """

        # Extract url into parts
        ext = Path(url).suffix
        domain = str(Path(url).parents[0])
        name = Path(url).stem

        # Check url
        if (".gifv" in ext) and ("imgur" in domain):
            url = 'https://imgur.com/download/{id}'.format(id=name)

            # Modify dest extension from .gifv to .gif
            ext = '.gif'

        # Check for media.giphy files
        elif (".gif" in ext) and ("media.giphy" in domain):
            url = 'https://i.giphy.com/media/{id}/giphy.webp'.format(
                id=url.split('/')[-2])

            # Modify dest extension from .webp to .gif
            ext = '.gif'

        # Check for gfycat (N.B. Needs to converting from .mp4 to .gif)
        elif "gfycat.com" in domain:
            url = 'https://thumbs.gfycat.com/{id}-mobile.mp4'.format(id=name)

            # Modify dest extension from .webp to .gif
            ext = '.mp4'

        # Check for v.reddit videos (N.B. Needs to converting from .mp4 to 
        # .gif).
        elif "v.redd.it" in domain:
            url = 'https://v.redd.it/{id}/DASH_1080?source=fallback'.format(
                id=name)

            # Modify dest extension from .webp to .gif
            ext = '.mp4'

        return url, ext

    def _download_image(self, source_url, dest_url):

        # Check for imgur .gifv files. Must be converted into a .gif
        source_url, ext = self._check_media_type(source_url)

        print("URL", source_url, dest_url)

        print("[INFO] Deleting: {fname}".format(fname=dest_url))

        # Delete any file in dest_url
        if os.path.exists(dest_url):
            os.remove(dest_url)

        # Convert video to .gif and download.
        if 'mp4' in ext:
            # Append extension to url
            # dest_url += '.gif'

            # Convert video file
            try:
                VideoFileClip(source_url).write_gif(
                    dest_url, program='ffmpeg', fps=25)
            except OSError:
                print("[WARNING] Couldn't convert video to .gif :(")

        # Download the image.
        else:
            # Append extension to url
            # dest_url += ext

            urllib.request.urlretrieve(source_url, dest_url)

    def _panda_list(self, method='top', limit=10, save=False):
        """Gets a list of all the panda images. Does not download them.
        """

        needs_saving = False

        if save:

            # Make sure to expand any user variables
            save = str(Path(os.path.expandvars(save)))

            # Attempt to open file
            try:
                panda_urls = np.genfromtxt(save, delimiter=',', dtype=str)
                return panda_urls

            except OSError:
                needs_saving = True

        panda_urls = []
        for image in getattr(self.reddit.subreddit('redpandas'), 
        #for image in getattr(self.reddit.subreddit('rickandmorty'), 
                method)(time_filter='all', limit=limit):
            
            # Get image URL and extract URL.
            panda_urls.append(image.url)
        
        if needs_saving:
            np.savetxt(save, panda_urls, fmt='%s', delimiter=',')

        return panda_urls

    @staticmethod
    def _get_save_path(base_dir, subreddit, method, limit):
        
        save_path = "{base_dir}{subreddit}_{method}_{limit}_list.txt".format(
            base_dir=base_dir, 
            subreddit=subreddit,
            method=method,
            limit=limit)

        # Make sure to expand any user variables
        return str(Path(os.path.expandvars(save_path)))
        
    def _list(self, subreddit, type='both', method='top', limit=10, save=False, 
            refresh=False):
        """Gets a list of all the images from a subreddit. Does not 
        download them.
        """

        needs_saving = False

        # Get file name based on subreddit.
        save_path = self._get_save_path(self.base_dir, subreddit, 
            method=method, limit=limit)

        # Attempt to open file
        try:
            if not refresh:
                panda_urls = np.genfromtxt(save_path, delimiter=',', dtype=str)
                return panda_urls

        except OSError:
            pass
        finally:
            needs_saving = True

        panda_urls = []
        for image in getattr(self.reddit.subreddit(subreddit), 
                method)(time_filter='all', limit=limit):
            
            # Get image URL and extract URL.
            panda_urls.append(image.url)
        
        if needs_saving:
            np.savetxt(save_path, panda_urls, fmt='%s', delimiter=',')

        return panda_urls

    def _update_terminal(self, url):
        """Update the new Microsoft terminal background image.
        """

        print("[INFO] Updating Microsoft Terminal...")
        
        with open(self.settings_path, 'r') as file:
            json_file = json.load(file)

        json_file['profiles'][1]['backgroundImage'] = url + 'tmp'

        with open(self.settings_path, 'w') as file:
            json.dump(json_file, file)

        time.sleep(0.5)

        json_file['profiles'][1]['backgroundImage'] = url

        with open(self.settings_path, 'w') as file:
            json.dump(json_file, file)

    def _update_windows_background(self, url):
        """
        """

        SPI_SETDESKWALLPAPER = 20 
        
        # Check platform is Windows:
        if 'win' in sys.platform:
            if platform.machine().endswith('64'):
                ctypes.windll.user32.SystemParametersInfoW(
                    SPI_SETDESKWALLPAPER, 0, url , 0)
            else:
                ctypes.windll.user32.SystemParametersInfoA(
                    SPI_SETDESKWALLPAPER, 0, url , 0)
        else:
            raise OSError("Only supported for Windows machines!")

    def download_pandas(self, method='top', limit=10):
        """Downloads red panda images from reddit. The number of images
        and method of how to download them is configurable.
        """

        # Get top posts of red pandas
        for i, image in enumerate(getattr(self.reddit.subreddit('redpandas'), 
                method)(time_filter='all', limit=limit)):
            
            # Get image URL and extract URL.
            source_url = image.url
            
            # Build the destination URL.
            dest_url = os.path.expandvars("%USERPROFILE%/Downloads/red_panda/red_panda_reddit_" \
                "{num}".format(num=str(i).rjust(3,'0')))

            # Download image
            self._download_image(source_url, dest_url)
            

    def get_panda(self, method='top', limit=1000, weight=True, no_ext=False,
            save=False, recreate_list=False, update_terminal=False):
        """Gets a single panda image at random."""

        # Get the Red Pandas
        dest_url = self.get('redpandas', method=method, limit=limit, 
            weight=weight)

        # Update the microsoft terminal.
        if update_terminal:
            self._update_terminal(dest_url)

    def _filter(self, url_list, type='both'):
        """Filter the list of images by image type.
        """

        image_formats = ['jpg', 'bmp', 'png', 'jpeg', 'tiff']
        animated_formats = ['mp4', 'gif']

        for url in url_list:
            _, ext = self._check_media_type(url)

            #if ext in 

    def get(self, subreddit, type='both', method='top', limit=1000, 
            weight=True, refresh=False):
        """Gets a single image/video from a subreddit.
        """

        # Get top posts of red pandas
        panda_urls = self._list(subreddit, method=method, 
            limit=limit, refresh=refresh)

        # Filter urls by type
        # panda_urls = self._filter(panda_urls, type)

        # Update limit now the number of urls have been filtered.
        limit = len(panda_urls)

        # Randomise
        if weight:
            select = np.ceil(np.random.lognormal(mean=2, sigma=1, size=1))
        else:
            select = np.random.randint(low=1, high=limit, size=1)

        # Clip
        select = np.clip(select, 1, limit).astype(np.int)[0]

        # Build the destination URL.
        dest_url = os.path.expandvars(self.image_path.format(
            subreddit=subreddit, key='RANDOM'))

        # Select random image to download.
        self._download_image(panda_urls[select], dest_url)

        return dest_url

    def update_terminal(self, subreddit, method='top', limit=1000, weight=True, 
            refresh=False):
        """Randomly gets a single image/video from a subreddit and 
        updates the new Microsoft Terminal.

        :param subreddit : str
            The subreddit you want to get an image/gif/video from.
        :param method : str, optional
            The method you want to filter the reddit posts by. Choose 
            either 'top' | 'hot' | 'controversial' | 'rising'.
        :param limit : int, optional
            Limit the number of graphics you want to randomly select 
            against. Default is 1000.
        :param weight : bool, optional
            Specify whether to weight the random pick towards the top
            graphics (True) or have an equal chance at all graphics 
            (False). Default is True.
        :param refresh : bool, optional
            Specify whether to refresh the list of graphics. Useful if 
            there is an error or its been a while since using this 
            program.  
        """

        dest_url = self.get(subreddit, method=method, limit=limit, 
            weight=weight, refresh=refresh)

        # Update the microsoft terminal.
        self._update_terminal(dest_url)

    def update_windows_background(self, subreddit, method='top', limit=1000, weight=True, 
            refresh=False):
        """Randomly gets a single image/video from a subreddit and 
        updates the windows background.

        :param subreddit : str
            The subreddit you want to get an image/gif/video from.
        :param method : str, optional
            The method you want to filter the reddit posts by. Choose 
            either 'top' | 'hot' | 'controversial' | 'rising'.
        :param limit : int, optional
            Limit the number of graphics you want to randomly select 
            against. Default is 1000.
        :param weight : bool, optional
            Specify whether to weight the random pick towards the top
            graphics (True) or have an equal chance at all graphics 
            (False). Default is True.
        :param refresh : bool, optional
            Specify whether to refresh the list of graphics. Useful if 
            there is an error or its been a while since using this 
            program.  
        """
        
        # Only download images from subreddit as animated gifs nor videos
        # can be used as backgrounds.
        dest_url = self.get(subreddit, type='image', method=method, 
            limit=limit, weight=weight, refresh=refresh)

        # Update the windows desktop background.
        self._update_windows_background(dest_url)

if __name__ == "__main__":

    # Load in client ID and client secrets from file
    with open('secrets.ini', 'r') as file:
        client_id, client_secret, user_agent, base_dir = \
            file.readline().split(",")

    # Initalise red panda instance
    pandas = RedditPanda(client_id, client_secret, user_agent, base_dir)

    # Download 100 top images of red pandas.
    # pandas.download_pandas(method='top', limit=100)

    # Get a single panda image at random
    while True:
        pandas.update_terminal('redpandas', refresh=False)

        time.sleep(5)