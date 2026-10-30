"""Open work from the original JobsList table, shared by homepage and workspace."""
import legacy_jobs
from market_service import money, today


def open_jobs(store, limit=80):
    rows=[]
    for row in legacy_jobs.list_jobs(store,limit=limit,open_only=True):
        try:
            amount=money(row['Price']) if row.get('Price') is not None else None
        except ValueError:
            amount=None
        rows.append(dict(Id=row['Jobid'],Title=row['Title'],Kind='bid' if str(row.get('BitOrContest') or '').strip().lower() in {'bit','bid'} else 'contest',
                         Budget=amount,Deadline=str(row['Deadline'])[:10],Description=row.get('Description') or '',
                         Source='existing',Endpoint='market.existing_job_detail',Category=row.get('Type') or 'General'))
    return rows[:limit]
