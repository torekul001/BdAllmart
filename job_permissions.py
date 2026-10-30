"""Job-side permissions shared by the existing and unified workspaces."""
def category(value):
    return str(value or '').strip().lower().replace(' ', '').replace('-', '')


def can_post(category_name):
    return category(category_name) in {'admin', 'customer', 'consumer', 'buyer', 'vendor', 'seller', 'user'}


def can_apply(category_name):
    return category(category_name) in {'admin', 'designer', 'freelancer'}


def actor_category(store, user_id, admin=False):
    if admin:
        return 'admin'
    row = store.one('SELECT UserCatagory FROM Users WHERE UserId=?', [str(user_id)])
    return category(row['UserCatagory']) if row else ''
