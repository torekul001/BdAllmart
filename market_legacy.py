"""Read-only legacy catalog bridge: existing stock/checkout stays authoritative."""
import logging

log = logging.getLogger(__name__)


def products(store, query="", owner_id=None):
    # Isolated new-module tests intentionally do not provision legacy catalog tables.
    if store.sqlite:
        return [], ""
    try:
        username = ""
        params = ["%" + query + "%"]
        sql = """SELECT P.PID,P.PName,P.PPrice,P.PSelPrice,I.Name,I.Extention
            FROM tblProducts P
            LEFT JOIN (SELECT PID, MIN(Name) AS Name, MIN(Extention) AS Extention
                       FROM tblProductImages GROUP BY PID) I ON I.PID=P.PID
            WHERE EXISTS (SELECT 1 FROM Productbarcode B WHERE B.Item_Id=P.PID AND B.Status='OK')
            AND P.PName LIKE ?"""
        if owner_id:
            owner = store.one("SELECT Username FROM Users WHERE UserId=?", [str(owner_id)])
            if not owner:
                return [], ""
            username = str(owner["Username"])
            sql += """ AND (P.MainItemSellerName=? OR EXISTS
                (SELECT 1 FROM DesignerAffiliateProducts A WHERE A.DesignerUserId=?
                 AND A.ProductId=CAST(P.PID AS varchar(100)) AND A.Status='Active'))"""
            params.extend([username, str(owner_id)])
        return store.page(sql + " ORDER BY P.PID DESC", params, limit=12), username
    except Exception:
        log.exception("Legacy catalog bridge unavailable")
        return [], ""
