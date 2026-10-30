"""Adapter for the existing AllServicer JobsList / JobAppliedList workflow.

Field names follow App_Code/DAL.cs SaveAppliedJob. CustomerId in that table
is the applying Designer's ID, as in the original C# implementation.
"""
from datetime import datetime, timezone
from decimal import Decimal
import json
import html
import re
from job_permissions import actor_category, can_apply, can_post
from market_service import require, text, money, today, uid, now, meta


def migrate_applications(store):
    if store.sqlite:
        store.run('''CREATE TABLE IF NOT EXISTS JobAppliedList (
            Id INTEGER PRIMARY KEY AUTOINCREMENT, Type TEXT NOT NULL, Jobid INTEGER NOT NULL,
            Title TEXT NOT NULL, CustomerId TEXT NOT NULL, CustomerName TEXT NOT NULL,
            Date TEXT NOT NULL, SetBudget DECIMAL(18,2), Msg TEXT NOT NULL,
            UNIQUE(Jobid,CustomerId))''')
    else:
        store.run('''IF OBJECT_ID(N'dbo.JobAppliedList',N'U') IS NULL
            CREATE TABLE dbo.JobAppliedList (
            Id BIGINT IDENTITY(1,1) PRIMARY KEY, Type NVARCHAR(30) NOT NULL,
            Jobid INT NOT NULL, Title NVARCHAR(500) NOT NULL,
            CustomerId NVARCHAR(100) NOT NULL, CustomerName NVARCHAR(160) NOT NULL,
            [Date] DATETIME2 NOT NULL, SetBudget DECIMAL(18,2) NULL,
            Msg NVARCHAR(MAX) NOT NULL, UNIQUE(Jobid,CustomerId))''')


def list_jobs(store, user_id='', limit=80, open_only=True):
    if store.sqlite and not store.one("SELECT name FROM sqlite_master WHERE type='table' AND name='JobsList'"):
        return []
    sql='''SELECT Jobid,Title,Type,Description,Deadline,Price,Customerid,BitOrContest,Status
        FROM JobsList WHERE (Deadline>=? AND LOWER(LTRIM(RTRIM(COALESCE(Status,'')))) IN ('true','1','active')
        AND LOWER(LTRIM(RTRIM(COALESCE(BitOrContest,'contest')))) IN ('bit','bid','contest'))'''
    params=[today().isoformat()]
    if not open_only:
        sql+=' OR CAST(Customerid AS VARCHAR(100))=?'
        params.append(str(user_id))
    return store.page(sql+' ORDER BY Jobid DESC',params,limit=limit)


def my_applications(store,user_id):
    if store.sqlite and not store.one("SELECT name FROM sqlite_master WHERE type='table' AND name='JobAppliedList'"):
        return []
    return store.page('SELECT Jobid,Type,Title,SetBudget,Msg,[Date] FROM JobAppliedList WHERE CustomerId=? ORDER BY [Date] DESC', [str(user_id)],limit=30)


def get_job(store, job_id):
    return store.one('SELECT * FROM JobsList WHERE Jobid=?', [job_id])


def apply_to_job(store, user_id, job_id, data, admin=False):
    require(can_apply(actor_category(store,user_id,admin)), 'Only Designer / Freelancer accounts can apply.')
    hint = ' WITH (UPDLOCK,HOLDLOCK)' if not store.sqlite else ''
    job = store.one(f'SELECT * FROM JobsList{hint} WHERE Jobid=?', [job_id])
    require(job, 'Job not found.')
    require(str(job['Customerid']) != str(user_id), 'You cannot apply to your own job.')
    require(str(job.get('Deadline') or '')[:10]>=today().isoformat(), 'The submission deadline has passed.')
    require(str(job.get('Status') or '').strip().lower() in {'true','1','active'}, 'This job is closed.')
    kind = str(job.get('BitOrContest') or 'Contest').strip().lower()
    require(kind in {'bit','bid','contest'}, 'Designers can apply to Bid / Contest jobs only.')
    body = text(data.get('body'), 'application message',6000)
    amount = money(data.get('amount')) if kind in {'bit','bid'} else None
    if amount is not None:
        require(amount>0, 'Enter a bid amount greater than zero.')
    account = store.one('SELECT Username FROM Users WHERE UserId=?', [str(user_id)])
    require(account, 'User not found.')
    previous = store.one('SELECT * FROM JobAppliedList WHERE Jobid=? AND CustomerId=?', [job_id,str(user_id)])
    budget = str(Decimal(amount)/100) if amount is not None else None
    stamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=' ', timespec='seconds')
    if previous:
        store.run('UPDATE JobAppliedList SET SetBudget=?,Msg=?,[Date]=? WHERE Jobid=? AND CustomerId=?',
                  [budget,body,stamp,job_id,str(user_id)])
    else:
        store.run('''INSERT INTO JobAppliedList (Type,Jobid,Title,CustomerId,CustomerName,[Date],SetBudget,Msg)
            VALUES (?,?,?,?,?,?,?,?)''', ['Bit' if kind in {'bit','bid'} else 'Contest',job_id,str(job.get('Title') or ''),
            str(user_id),str(account['Username']),stamp,budget,body])
    return kind


def job_submissions(store,job_id,user_id='',all_entries=False):
    if store.sqlite and not store.one("SELECT name FROM sqlite_master WHERE type='table' AND name='Submission'"):
        return []
    sql='''SELECT S.subid,S.userid,S.title,S.jpgfile,S.date,S.status,S.feedback,U.Username
        FROM Submission S LEFT JOIN Users U ON U.UserId=S.userid WHERE S.jobid=?'''
    params=[job_id]
    if not all_entries:
        sql+=' AND S.userid=?'
        params.append(str(user_id))
    return store.all(sql+' ORDER BY S.date DESC',params)


def select_designer(svc,job_id,data):
    """Select a bid / contest winner and reuse the full order delivery workflow."""
    store=svc.db
    require(svc.admin or can_post(actor_category(store,svc.user)), 'Only the Customer can select a designer.')
    hint=' WITH (UPDLOCK,HOLDLOCK)' if not store.sqlite else ''
    job=store.one(f'SELECT * FROM JobsList{hint} WHERE Jobid=?',[job_id])
    require(job and (svc.admin or str(job['Customerid'])==svc.user),'Only the job owner can select a designer.')
    mapping=store.get('MarketLegacyContract',job_id,True)
    if mapping:
        previous=store.get('MarketOrder',mapping['OrderId'],True)
        if previous and previous['Status'] not in {'cancelled','refunded'}:
            return previous['Id']
    require(str(job.get('Status') or '').strip().lower() in {'true','1','active'},'This job is closed.')
    kind=str(job.get('BitOrContest') or 'Contest').strip().lower()
    require(kind in {'bit','bid','contest'},'Select a Bid / Contest job.')
    submission_id=''
    if kind in {'bit','bid'}:
        application=store.one('SELECT * FROM JobAppliedList WHERE Jobid=? AND CustomerId=?',[job_id,str(data.get('designer_id',''))])
        require(application,'Choose a designer who applied to this job.')
        designer=str(application['CustomerId'])
        amount=money(application['SetBudget'])
        proposal=str(application.get('Msg') or '')
    else:
        submission_id=text(data.get('submission_id'),'contest submission',100)
        entry=store.one('SELECT * FROM Submission WHERE subid=? AND jobid=?',[submission_id,job_id])
        require(entry,'Choose a submission belonging to this contest.')
        designer=str(entry['userid'])
        amount=money(job.get('Price'))
        proposal='Contest entry: '+str(entry.get('title') or '')
    require(designer != str(job['Customerid']),'You cannot hire yourself.')
    require(can_apply(actor_category(store,designer)),'The selected user must be a Designer / Freelancer.')
    account=store.one('SELECT Username,Active,Status FROM Users WHERE UserId=?',[designer])
    require(account and str(account['Active']).strip().lower() in {'1','true'} and str(account['Status'] or '').strip().lower() in {'','true'},'The designer account is inactive.')
    require(amount>0,'The agreed price must be greater than zero.')
    if not svc.profile(designer,True):
        store.insert('MarketProfile',dict(UserId=designer,DisplayName=str(account['Username']),Bio='',Business=0,InstituteStatus='none'))
    order_id=uid()
    brief=re.sub(r'<[^>]*>','',html.unescape(str(job.get('Description') or '')))+'\n\nAccepted proposal: '+proposal
    details={'legacy_job_id':job_id,'legacy_submission_id':submission_id,'revisions':2,
             'deadline':str(job.get('Deadline') or '')[:10],
             'terms':'Agreed price is fixed at selection. Work begins after verified payment. Two revisions are included. Customer accepts final delivery to complete the contract.'}
    store.insert('MarketOrder',dict(Id=order_id,BuyerId=str(job['Customerid']),SellerId=designer,ListingId='',ProposalId='',Kind='job',
        Title=html.unescape(str(job.get('Title') or 'Job'))[:180],Amount=amount,Quantity=1,Status='placed',PaymentStatus='pending',
        PaymentRef='',ReferrerId='',Commission=0,Brief=brief,Delivery='',Asset='',Meta=json.dumps(details),RequestKey=uid(),Created=now()))
    values=dict(OrderId=order_id,DesignerId=designer,SubmissionId=submission_id,Created=now())
    if mapping:
        store.update('MarketLegacyContract',job_id,values)
    else:
        store.insert('MarketLegacyContract',dict(Id=str(job_id),**values))
    store.run("UPDATE JobsList SET Status='False' WHERE Jobid=?",[job_id])
    if submission_id:
        store.run("UPDATE Submission SET status='Selected',Price=? WHERE subid=? AND jobid=?",[str(Decimal(amount)/100),submission_id,job_id])
    svc.event(order_id,'contract.created',f'Existing JobsList #{job_id}',designer)
    return order_id


def sync_contract(svc,order,action):
    """Keep existing JobsList/Submission states consistent with the linked contract."""
    job_id=meta(order).get('legacy_job_id')
    if not job_id:
        return
    mapping=svc.db.get('MarketLegacyContract',job_id,True)
    if not mapping or mapping['OrderId']!=order['Id']:
        return
    if action=='cancel':
        job=get_job(svc.db,job_id)
        status='True' if job and str(job.get('Deadline') or '')[:10]>=today().isoformat() else 'False'
        svc.db.run('UPDATE JobsList SET Status=? WHERE Jobid=?',[status,job_id])
    else:
        svc.db.run("UPDATE JobsList SET Status='False' WHERE Jobid=?",[job_id])
    if mapping['SubmissionId'] and action in {'cancel','refund','complete','resolve'}:
        status={'cancel':'Cancelled','refund':'Refunded','complete':'Selected','resolve':'Selected'}[action]
        svc.db.run('UPDATE Submission SET status=? WHERE subid=? AND jobid=?',[status,mapping['SubmissionId'],job_id])
