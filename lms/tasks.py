from celery import shared_task


@shared_task
def test_task():
    print("Celery berhasil berjalan")
    return "success"