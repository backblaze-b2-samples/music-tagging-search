"""Local OSS audio models. None of these ever touch B2 directly — they
operate on local files handed to them by the service layer, which gets those
bytes from the repo S3 client (so the custom user agent always holds)."""
