from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple, AnyStr, Any

import aiohttp

from .base_functions import *


@dataclass
class AlbumItem:
    """Class for keeping track of download links for each album"""
    title: str
    link_pairs: List[Tuple]
    password: Optional[str] = None

    async def add_link_pair(self, link, referral):
        self.link_pairs.append((link, referral))

    async def set_new_title(self, new_title: str):
        self.title = new_title


@dataclass
class DomainItem:
    domain: str
    albums: Dict[str, AlbumItem]

    async def add_to_album(self, title: str, link: URL, referral: URL):
        if title in self.albums.keys():
            await self.albums[title].add_link_pair(link, referral)
        else:
            self.albums[title] = AlbumItem(title=title, link_pairs=[(link, referral)])

    async def add_album(self, title: str, album: AlbumItem):
        if title in self.albums.keys():
            stored_album = self.albums[title]
            for link_pair in album.link_pairs:
                link, referral = link_pair
                await stored_album.add_link_pair(link, referral)
        else:
            self.albums[title] = album


@dataclass
class CascadeItem:
    """Class for keeping track of domains for each scraper type"""
    domains: Dict[str, DomainItem]
    cookies: aiohttp.CookieJar = None

    async def add_albums(self, domain_item: DomainItem):
        domain = domain_item.domain
        albums = domain_item.albums
        for title, album in albums.items():
            await self.add_album(domain, title, album)

    async def add_to_album(self, domain: str, title: str, link: URL, referral: URL):
        if domain in self.domains.keys():
            await self.domains[domain].add_to_album(title, link, referral)
        else:
            self.domains[domain] = DomainItem(domain, {title: AlbumItem(title, [(link, referral)])})

    async def add_album(self, domain: str, title: str, album: AlbumItem):
        if domain in self.domains.keys():
            await self.domains[domain].add_album(title, album)
        else:
            self.domains[domain] = DomainItem(domain, {title: album})

    async def is_empty(self):
        for domain_str, domain in self.domains.items():
            for album_str, album in domain.albums.items():
                if album.link_pairs:
                    return False
        return True

    async def append_title(self, title):
        for domain_str, domain in self.domains.items():
            new_albums = {}
            for album_str, album in domain.albums.items():
                new_title = title+'/'+album_str
                new_albums[new_title] = album
                album.title = new_title
            domain.albums = new_albums

    async def extend(self, Cascade):
        if Cascade.domains:
            for domain_str, domain in Cascade.domains.items():
                for album_str, album in domain.albums.items():
                    await self.add_album(domain_str, album_str, album)

    async def dedupe(self):
        for domain_str, domain in self.domains.items():
            for album_str, album in domain.albums.items():
                check = []
                allowed = []
                for pair in album.link_pairs:
                    url, referrer = pair
                    if url in check:
                        continue
                    else:
                        check.append(url)
                        allowed.append(pair)
                album.link_pairs = allowed
