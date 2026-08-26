from core.cloudstorage.service.storageservice import object_key_from_url


def test_object_key_from_path_style_presigned_url():
    url = (
        "https://usc1.contabostorage.com/my-bucket/operations/product-images/"
        "user1/abc.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=abc+def"
    )
    assert (
        object_key_from_url(url, bucket="my-bucket")
        == "operations/product-images/user1/abc.jpg"
    )


def test_object_key_from_contabo_tenant_prefix():
    url = (
        "https://usc1.contabostorage.com/tenantid:my-bucket/operations/"
        "product-images/user1/abc.jpg?X-Amz-Signature=truncated"
    )
    assert (
        object_key_from_url(url, bucket="my-bucket")
        == "operations/product-images/user1/abc.jpg"
    )


def test_object_key_from_raw_key():
    assert (
        object_key_from_url("operations/product-images/x.png")
        == "operations/product-images/x.png"
    )


def test_object_key_ignores_external_urls():
    assert object_key_from_url("https://cdn.example.com/photo.jpg") is None
