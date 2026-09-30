"""Rank measured niche rates, retaining provenance."""
def rank_niches(data):
    groups = {}
    for exp in data['experiments']:
        row = groups.setdefault(exp['niche'], dict(niche=exp['niche'], sent=0, replies=0,
                                                   synthetic=False, user_entered=False))
        row['synthetic'] |= exp['synthetic']
        row['user_entered'] |= not exp['synthetic']
        for obs in exp['observations']:
            row['sent'] += obs['sent']
            row['replies'] += obs['replies']
    for row in groups.values():
        row['rate'] = row['replies'] / row['sent'] if row['sent'] else None
        row['thin_data'] = row['sent'] < 30
        row['provenance'] = 'mixed synthetic and user-entered' if row['synthetic'] and row['user_entered'] else 'synthetic' if row['synthetic'] else 'user-entered'
    return sorted(groups.values(), key=lambda r: (-(r['rate'] if r['rate'] is not None else -1), r['niche']))
