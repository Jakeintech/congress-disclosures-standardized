"""
Master Data Management (MDM) for Member Names.

Handles name normalization, nickname resolution, and alias mapping
to ensure consistent member identification across different data sources.
"""

import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Common nicknames mapping
NICKNAMES = {
    "bob": "robert",
    "rob": "robert",
    "bobby": "robert",
    "bill": "william",
    "billy": "william",
    "will": "william",
    "jim": "james",
    "jimmy": "james",
    "tom": "thomas",
    "tommy": "thomas",
    "dick": "richard",
    "rick": "richard",
    "mike": "michael",
    "matt": "matthew",
    "chris": "christopher",
    "dave": "david",
    "dan": "daniel",
    "danny": "daniel",
    "joe": "joseph",
    "steve": "stephen",
    "steven": "stephen",
    "tim": "timothy",
    "pat": "patrick",
    "pete": "peter",
    "jeff": "jeffrey",
    "greg": "gregory",
    "alex": "alexander",
    "andy": "andrew",
    "ben": "benjamin",
    "brad": "bradley",
    "don": "donald",
    "ed": "edward",
    "fred": "frederick",
    "jerry": "gerald",
    "ken": "kenneth",
    "larry": "lawrence",
    "nick": "nicholas",
    "ron": "ronald",
    "sam": "samuel",
    "ted": "theodore",
    "tony": "anthony",
    "zach": "zachary",
    "jake": "jacob",
    "josh": "joshua",
    "nate": "nathan",
    "gabe": "gabriel",
    "art": "arthur",
    "hal": "harold",
    "hank": "henry",
    "harry": "henry",
    "jack": "john",
    "peggy": "margaret",
    "meg": "margaret",
    "maggie": "margaret",
    "sue": "susan",
    "liz": "elizabeth",
    "beth": "elizabeth",
    "cathy": "catherine",
    "kate": "katherine",
    "katie": "katherine",
    "deb": "deborah",
    "debbie": "deborah",
    "patty": "patricia",
    "trish": "patricia",
    "becky": "rebecca",
    "vicky": "victoria",
    "ginny": "virginia"
}

# Known aliases for specific members (Filing Name -> Official Name)
KNOWN_ALIASES = {
    "buddy carter": ("earl", "carter"),
    "dutch ruppersberger": ("c.", "ruppersberger"),
    "chuck fleischmann": ("charles", "fleischmann"),
    "buddy carter": ("earl", "carter"),
    "chip roy": ("charles", "roy"),
    "french hill": ("james", "hill"),
    "pete sessions": ("peter", "sessions"),
    "pete aguilar": ("peter", "aguilar"),
    "pete stauber": ("peter", "stauber"),
    "bill huizenga": ("william", "huizenga"),
    "bill keating": ("william", "keating"),
    "bill pascrell": ("william", "pascrell"),
    "bill posey": ("william", "posey"),
    "bill foster": ("william", "foster"),
    "bill johnson": ("william", "johnson"),
    "bob latta": ("robert", "latta"),
    "bob good": ("robert", "good"),
    "bob menendez": ("robert", "menendez"),
    "bobby scott": ("robert", "scott"),
    "buddy carter": ("earl", "carter"),
    "dutch ruppersberger": ("c.", "ruppersberger"),
    "gus bilirakis": ("gustavus", "bilirakis"),
    "hal rogers": ("harold", "rogers"),
    "hank johnson": ("henry", "johnson"),
    "jack bergman": ("john", "bergman"),
    "jim banks": ("james", "banks"),
    "jim baird": ("james", "baird"),
    "jim costa": ("james", "costa"),
    "jim himes": ("james", "himes"),
    "jim jordan": ("james", "jordan"),
    "jim mcgovern": ("james", "mcgovern"),
    "joe courtney": ("joseph", "courtney"),
    "joe morelle": ("joseph", "morelle"),
    "joe neguse": ("joseph", "neguse"),
    "joe wilson": ("joseph", "wilson"),
    "kat cammack": ("kathryn", "cammack"),
    "kay granger": ("kay", "granger"),
    "kim schrier": ("kimberly", "schrier"),
    "mike bost": ("michael", "bost"),
    "mike carey": ("michael", "carey"),
    "mike collins": ("michael", "collins"),
    "mike ezell": ("michael", "ezell"),
    "mike flood": ("michael", "flood"),
    "mike garcia": ("michael", "garcia"),
    "mike guest": ("michael", "guest"),
    "mike johnson": ("james", "johnson"), # Speaker Mike Johnson is James Michael Johnson
    "mike kelly": ("michael", "kelly"),
    "mike lawler": ("michael", "lawler"),
    "mike levin": ("michael", "levin"),
    "mike quigley": ("michael", "quigley"),
    "mike rogers": ("michael", "rogers"),
    "mike simpson": ("michael", "simpson"),
    "mike thompson": ("michael", "thompson"),
    "mike turner": ("michael", "turner"),
    "mike waltz": ("michael", "waltz"),
    "pat fallon": ("patrick", "fallon"),
    "pat ryan": ("patrick", "ryan"),
    "rick crawford": ("eric", "crawford"),
    "rick larsen": ("richard", "larsen"),
    "rick allen": ("richard", "allen"),
    "rob wittman": ("robert", "wittman"),
    "rob menendez": ("robert", "menendez"),
    "russ fulcher": ("russell", "fulcher"),
    "sam graves": ("samuel", "graves"),
    "steve cohen": ("stephen", "cohen"),
    "steve scalise": ("stephen", "scalise"),
    "steve womack": ("stephen", "womack"),
    "susie lee": ("suzanne", "lee"),
    "ted lieu": ("ted", "lieu"),
    "tim burchett": ("timothy", "burchett"),
    "tim walberg": ("timothy", "walberg"),
    "tom cole": ("thomas", "cole"),
    "tom emmer": ("thomas", "emmer"),
    "tom kean": ("thomas", "kean"),
    "tom mcclintock": ("thomas", "mcclintock"),
    "tom suozzi": ("thomas", "suozzi"),
    "tom tiffany": ("thomas", "tiffany"),
    "tommy tuberville": ("thomas", "tuberville"),
    "vicente gonzalez": ("vicente", "gonzalez"),
    "virginia foxx": ("virginia", "foxx"),
}

class MemberNameNormalizer:
    """Normalizes member names for better matching."""

    @staticmethod
    def normalize(first_name: str, last_name: str) -> Tuple[str, str]:
        """
        Normalize first and last name using MDM rules.
        
        1. Check known aliases (exact match)
        2. Clean whitespace/case
        3. Resolve nicknames to formal names
        4. Strip middle names/initials from first name
        """
        if not first_name or not last_name:
            return first_name, last_name

        # 1. Clean basic
        first = first_name.lower().strip().replace('.', '')
        last = last_name.lower().strip().replace('.', '')
        full_key = f"{first} {last}"

        # 2. Check aliases
        if full_key in KNOWN_ALIASES:
            return KNOWN_ALIASES[full_key]

        # 3. Handle "First M." pattern
        parts = first.split()
        if len(parts) > 1:
            # Assume first part is the actual first name
            first = parts[0]

        # 4. Resolve nickname
        if first in NICKNAMES:
            first = NICKNAMES[first]

        return first, last
