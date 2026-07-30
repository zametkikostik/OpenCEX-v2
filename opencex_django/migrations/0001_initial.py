from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="UserKYC",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("none", "None"), ("pending", "Pending"), ("in_progress", "In Progress"), ("approved", "Approved"), ("rejected", "Rejected"), ("expired", "Expired"), ("revoked", "Revoked")], db_index=True, default="none", max_length=32)),
                ("level", models.CharField(blank=True, choices=[("meid", "MeID"), ("zkkyc", "zkKYC"), ("aml", "AML"), ("existing", "Existing KYC")], max_length=32, null=True)),
                ("provider", models.CharField(blank=True, choices=[("zkme", "zkMe"), ("zkpass", "zkPass"), ("privado", "Privado ID"), ("sumsub", "Sumsub")], max_length=32, null=True)),
                ("claims", models.JSONField(blank=True, default=dict)),
                ("credential_id", models.CharField(blank=True, max_length=255, null=True)),
                ("proof_hash", models.CharField(blank=True, max_length=255, null=True)),
                ("session_id", models.CharField(blank=True, max_length=64, null=True)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("history", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="opencex_kyc", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "User KYC", "verbose_name_plural": "User KYC records"},
        ),
        migrations.CreateModel(
            name="WalletSessionRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_id", models.CharField(db_index=True, max_length=64, unique=True)),
                ("mode", models.CharField(choices=[("custodial", "Custodial"), ("non_custodial", "Non-Custodial"), ("hybrid", "Hybrid")], max_length=32)),
                ("address", models.CharField(blank=True, db_index=True, max_length=42, null=True)),
                ("chain_id", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("meta", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="wallet_sessions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SignedOrderRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_id", models.CharField(db_index=True, max_length=64, unique=True)),
                ("chain_id", models.PositiveIntegerField()),
                ("sell_token", models.CharField(max_length=42)),
                ("buy_token", models.CharField(max_length=42)),
                ("sell_amount", models.CharField(max_length=78)),
                ("min_buy_amount", models.CharField(max_length=78)),
                ("nonce", models.PositiveIntegerField()),
                ("expiry", models.PositiveIntegerField()),
                ("signature", models.TextField()),
                ("signer", models.CharField(db_index=True, max_length=42)),
                ("status", models.CharField(choices=[("open", "Open"), ("filled", "Filled"), ("cancelled", "Cancelled"), ("expired", "Expired"), ("failed", "Failed")], db_index=True, default="open", max_length=32)),
                ("typed_data", models.JSONField(blank=True, default=dict)),
                ("fill_tx_hash", models.CharField(blank=True, max_length=66, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="signed_orders", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SwapExecution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("client_order_id", models.CharField(blank=True, db_index=True, max_length=64, null=True)),
                ("chain_id", models.PositiveIntegerField()),
                ("sell_symbol", models.CharField(max_length=32)),
                ("buy_symbol", models.CharField(max_length=32)),
                ("sell_token", models.CharField(max_length=42)),
                ("buy_token", models.CharField(max_length=42)),
                ("sell_amount", models.CharField(max_length=78)),
                ("expected_buy_amount", models.CharField(blank=True, max_length=78, null=True)),
                ("actual_buy_amount", models.CharField(blank=True, max_length=78, null=True)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("locking", "Locking"), ("broadcasting", "Broadcasting"), ("confirming", "Confirming"), ("success", "Success"), ("failed", "Failed"), ("reverted", "Reverted")], db_index=True, default="queued", max_length=32)),
                ("tx_hash", models.CharField(blank=True, db_index=True, max_length=66, null=True)),
                ("block_number", models.PositiveBigIntegerField(blank=True, null=True)),
                ("error", models.TextField(blank=True, null=True)),
                ("plan", models.JSONField(blank=True, default=dict)),
                ("celery_task_id", models.CharField(blank=True, max_length=64, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="swap_executions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
