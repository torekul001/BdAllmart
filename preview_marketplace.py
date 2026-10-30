"""Export isolated sample pages for visual QA; never writes to the production database."""
from pathlib import Path
from test_marketplace import PortalTest


def main():
    test = PortalTest()
    test.setUp()
    try:
        test.seller.save_profile({"name": "Creative Studio", "bio": "Software, design and learning opportunities", "business": "1"})
        for kind in ("product", "service", "software", "course"):
            identity = test.listing(kind, title={"product": "Everyday Essentials Package", "service": "Brand Design for Your Business", "software": "Business Management Software", "course": "Complete Web Design Course"}[kind])
            if kind == "product":
                test.order(identity)
        test.connection.commit()
        output = Path(__file__).resolve().parent / "instance" / "ui_preview"
        output.mkdir(parents=True, exist_ok=True)
        static_url = (Path(__file__).resolve().parent / "static").as_uri() + "/"
        test.store.update('MarketProfile', 'buyer', {'Business':0})
        test.seed_existing_jobs()
        test.connection.commit()
        for name, endpoint in {"dashboard": "/workspace/", "catalog": "/workspace/catalog", "listing_form": "/workspace/listings", "settings": "/workspace/settings", "jobs": "/workspace/jobs"}.items():
            response = test.client.get(endpoint)
            assert response.status_code == 200
            content = response.get_data(as_text=True).replace('"/static/', '"' + static_url)
            (output / (name + ".html")).write_text(content, encoding="utf-8")
        test.login('seller','Designer')
        content=test.client.get('/workspace/jobs').get_data(as_text=True).replace('"/static/', '"'+static_url)
        (output/'jobs_designer.html').write_text(content,encoding='utf-8')
        from legacy_jobs import apply_to_job, select_designer
        apply_to_job(test.store,'seller',1,{'amount':'125','body':'I will complete this project.'})
        test.connection.commit()
        test.login('buyer')
        content=test.client.get('/workspace/existing-jobs/1').get_data(as_text=True).replace('"/static/', '"'+static_url)
        (output/'job_bid.html').write_text(content,encoding='utf-8')
        contract=select_designer(test.buyer,1,{'designer_id':'seller'})
        test.connection.commit()
        content=test.client.get('/workspace/orders/'+contract).get_data(as_text=True).replace('"/static/', '"'+static_url)
        (output/'job_contract.html').write_text(content,encoding='utf-8')
        for name, template in {'customer_module':'customer_dashboard', 'designer_module':'designer_dashboard', 'tracking_module':'customer_order_tracking'}.items():
            content = test.render_module(template).replace('"/static/', '"' + static_url)
            (output / (name + '.html')).write_text(content, encoding='utf-8')
        print(f"Isolated visual QA pages: {output}")
    finally:
        test.tearDown()


if __name__ == "__main__":
    main()
