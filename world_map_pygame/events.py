"""
World Map — Event Log
Tracks world events (conquests, awakenings, etc.).
"""
from datetime import datetime


class EventLog:
    def __init__(self, max_events=100):
        self.events     = []
        self.max_events = max_events

    def add(self, etype, description, god_id=None, zone=None):
        self.events.append({
            'type':        etype,
            'description': description,
            'god_id':      god_id,
            'zone':        zone,
            'timestamp':   datetime.now().isoformat(),
        })
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    def get_display(self, count=5):
        return [e['description'] for e in reversed(self.events[-count:])]

    def load_from_state(self, raw_events):
        for evt in raw_events:
            self.events.append({
                'type':        evt.get('type', 'unknown'),
                'description': self.format(evt),
                'god_id':      evt.get('god_id'),
                'zone':        evt.get('zone_id'),
                'timestamp':   evt.get('timestamp', ''),
            })

    @staticmethod
    def format(evt):
        t = evt.get('type', '')
        if t == 'territory_conquered':
            ch  = evt.get('champion', '???')
            god = evt.get('god_id', '').replace('god_', '').title()
            return f"{ch} ({god}) conquers territory"
        if t == 'territory_claimed':
            god = evt.get('god_id', '').replace('god_', '').title()
            return f"{god} claims new domain"
        if t == 'awakening':
            god = evt.get('god_id', '').replace('god_', '').title()
            return f"{god} awakens"
        return t.replace('_', ' ').title() if t else "Unknown event"
