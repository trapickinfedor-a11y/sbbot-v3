"""
Alembic migration: Sync with Mini App v2

Revision ID: sync_mini_app_v2
Revises: previous_revision
Create Date: 2026-03-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'sync_mini_app_v2'
down_revision = 'previous_revision'  # Replace with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade database to sync with Mini App v2"""
    
    # ============================================
    # 1. Banks Section - Rename and extend table
    # ============================================
    op.rename_table('seller_bank_selfreg_items', 'seller_bank_items')
    
    # Add new columns for Banks section
    op.add_column('seller_bank_items', sa.Column('category', sa.String(20), nullable=True))
    op.add_column('seller_bank_items', sa.Column('bank_code', sa.String(50), nullable=True))
    op.add_column('seller_bank_items', sa.Column('product_type', sa.String(100), nullable=True))
    op.add_column('seller_bank_items', sa.Column('balance', sa.Numeric(10, 2), server_default='0', nullable=True))
    op.add_column('seller_bank_items', sa.Column('phone_can_swap', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('seller_bank_items', sa.Column('return_item_enabled', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('seller_bank_items', sa.Column('return_days', sa.Integer(), nullable=True))
    
    # Update existing records
    op.execute("UPDATE seller_bank_items SET category = 'personal' WHERE category IS NULL")
    op.execute("UPDATE seller_bank_items SET balance = 0 WHERE balance IS NULL")
    
    # ============================================
    # 2. Brute Bank - Add detailed fields
    # ============================================
    op.add_column('brute_bank_items', sa.Column('exact_balance', sa.String(50), nullable=True))
    op.add_column('brute_bank_items', sa.Column('account_number', sa.String(255), nullable=True))
    op.add_column('brute_bank_items', sa.Column('routing_number', sa.String(255), nullable=True))
    op.add_column('brute_bank_items', sa.Column('holder_name', sa.String(200), nullable=True))
    op.add_column('brute_bank_items', sa.Column('address', sa.String(500), nullable=True))
    op.add_column('brute_bank_items', sa.Column('state', sa.String(10), nullable=True))
    op.add_column('brute_bank_items', sa.Column('zip', sa.String(20), nullable=True))
    op.add_column('brute_bank_items', sa.Column('additional_info', sa.Text(), nullable=True))
    op.add_column('brute_bank_items', sa.Column('has_docs', sa.Boolean(), server_default='false', nullable=True))
    
    # ============================================
    # 3. CC - Add NON VBV pricing
    # ============================================
    op.add_column('seller_cc_items', sa.Column('seller_price_non_vbv', sa.Numeric(10, 2), nullable=True))
    op.add_column('seller_cc_items', sa.Column('buyer_price_non_vbv', sa.Numeric(10, 2), nullable=True))
    
    # Set default NON VBV prices to regular prices
    op.execute("UPDATE seller_cc_items SET seller_price_non_vbv = seller_price WHERE seller_price_non_vbv IS NULL")
    op.execute("UPDATE seller_cc_items SET buyer_price_non_vbv = buyer_price WHERE buyer_price_non_vbv IS NULL")
    
    # ============================================
    # 4. Selfreg CC - Add new fields
    # ============================================
    op.add_column('seller_selfreg_cc_items', sa.Column('registration_date', sa.Date(), nullable=True))
    op.add_column('seller_selfreg_cc_items', sa.Column('vcc_bin', sa.String(6), nullable=True))
    op.add_column('seller_selfreg_cc_items', sa.Column('return_item_enabled', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('seller_selfreg_cc_items', sa.Column('return_days', sa.Integer(), nullable=True))
    
    # ============================================
    # 5. OTP - Add Fullz fields
    # ============================================
    op.add_column('seller_otp_items', sa.Column('state', sa.String(10), nullable=True))
    op.add_column('seller_otp_items', sa.Column('zip', sa.String(20), nullable=True))
    op.add_column('seller_otp_items', sa.Column('fullz_first_name', sa.String(100), nullable=True))
    op.add_column('seller_otp_items', sa.Column('fullz_last_name', sa.String(100), nullable=True))
    op.add_column('seller_otp_items', sa.Column('fullz_dob', sa.Date(), nullable=True))
    op.add_column('seller_otp_items', sa.Column('fullz_ssn', sa.String(20), nullable=True))
    op.add_column('seller_otp_items', sa.Column('fullz_address', sa.String(500), nullable=True))
    op.add_column('seller_otp_items', sa.Column('fullz_city', sa.String(100), nullable=True))
    op.add_column('seller_otp_items', sa.Column('fullz_state', sa.String(10), nullable=True))
    op.add_column('seller_otp_items', sa.Column('fullz_zip', sa.String(20), nullable=True))
    op.add_column('seller_otp_items', sa.Column('fullz_phone', sa.String(50), nullable=True))
    op.add_column('seller_otp_items', sa.Column('fullz_email', sa.String(200), nullable=True))
    
    # ============================================
    # 6. Enrollment - Add detailed fields
    # ============================================
    op.add_column('seller_enroll_items', sa.Column('first_name', sa.String(100), nullable=True))
    op.add_column('seller_enroll_items', sa.Column('last_name', sa.String(100), nullable=True))
    op.add_column('seller_enroll_items', sa.Column('dob', sa.Date(), nullable=True))
    op.add_column('seller_enroll_items', sa.Column('ssn', sa.String(20), nullable=True))
    op.add_column('seller_enroll_items', sa.Column('address', sa.String(500), nullable=True))
    op.add_column('seller_enroll_items', sa.Column('city', sa.String(100), nullable=True))
    op.add_column('seller_enroll_items', sa.Column('state', sa.String(10), nullable=True))
    op.add_column('seller_enroll_items', sa.Column('zip', sa.String(20), nullable=True))
    op.add_column('seller_enroll_items', sa.Column('phone', sa.String(50), nullable=True))
    op.add_column('seller_enroll_items', sa.Column('email', sa.String(200), nullable=True))
    op.add_column('seller_enroll_items', sa.Column('additional_info', sa.Text(), nullable=True))
    
    # ============================================
    # 7. Create Selfreg CC Card Names table
    # ============================================
    op.create_table(
        'selfreg_cc_card_names',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('card_name', sa.String(200), nullable=False),
        sa.Column('position', sa.Integer(), server_default='0', nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['selfreg_cc_categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_selfreg_cc_card_names_category_id', 'selfreg_cc_card_names', ['category_id'])
    
    # ============================================
    # 8. Add new Selfreg CC banks
    # ============================================
    op.execute("""
        INSERT INTO selfreg_cc_categories (code, name, position, is_active, is_custom) VALUES
        ('capital_one', 'Capital One', 5, TRUE, FALSE),
        ('discover', 'Discover', 6, TRUE, FALSE),
        ('amex', 'American Express', 7, TRUE, FALSE),
        ('usbank', 'US Bank', 8, TRUE, FALSE),
        ('pnc', 'PNC Bank', 9, TRUE, FALSE),
        ('td', 'TD Bank', 10, TRUE, FALSE),
        ('barclays', 'Barclays', 11, TRUE, FALSE),
        ('synchrony', 'Synchrony', 12, TRUE, FALSE)
        ON CONFLICT (code) DO NOTHING
    """)
    
    # ============================================
    # 9. Add Elan to Enroll categories
    # ============================================
    op.execute("""
        INSERT INTO enroll_categories (code, name, position, is_active, is_custom) VALUES
        ('elan', 'Elan', 12, TRUE, FALSE)
        ON CONFLICT (code) DO NOTHING
    """)
    
    # ============================================
    # 10. Create indexes for performance
    # ============================================
    op.create_index('ix_seller_bank_items_category', 'seller_bank_items', ['category'])
    op.create_index('ix_seller_bank_items_bank_code', 'seller_bank_items', ['bank_code'])
    op.create_index('ix_brute_bank_items_state', 'brute_bank_items', ['state'])
    op.create_index('ix_seller_otp_items_state', 'seller_otp_items', ['state'])


def downgrade():
    """Downgrade database (rollback changes)"""
    
    # Drop indexes
    op.drop_index('ix_seller_otp_items_state', 'seller_otp_items')
    op.drop_index('ix_brute_bank_items_state', 'brute_bank_items')
    op.drop_index('ix_seller_bank_items_bank_code', 'seller_bank_items')
    op.drop_index('ix_seller_bank_items_category', 'seller_bank_items')
    
    # Remove Elan from Enroll
    op.execute("DELETE FROM enroll_categories WHERE code = 'elan'")
    
    # Remove new Selfreg CC banks
    op.execute("""
        DELETE FROM selfreg_cc_categories 
        WHERE code IN ('capital_one', 'discover', 'amex', 'usbank', 'pnc', 'td', 'barclays', 'synchrony')
    """)
    
    # Drop Selfreg CC Card Names table
    op.drop_index('ix_selfreg_cc_card_names_category_id', 'selfreg_cc_card_names')
    op.drop_table('selfreg_cc_card_names')
    
    # Remove Enrollment fields
    op.drop_column('seller_enroll_items', 'additional_info')
    op.drop_column('seller_enroll_items', 'email')
    op.drop_column('seller_enroll_items', 'phone')
    op.drop_column('seller_enroll_items', 'zip')
    op.drop_column('seller_enroll_items', 'state')
    op.drop_column('seller_enroll_items', 'city')
    op.drop_column('seller_enroll_items', 'address')
    op.drop_column('seller_enroll_items', 'ssn')
    op.drop_column('seller_enroll_items', 'dob')
    op.drop_column('seller_enroll_items', 'last_name')
    op.drop_column('seller_enroll_items', 'first_name')
    
    # Remove OTP Fullz fields
    op.drop_column('seller_otp_items', 'fullz_email')
    op.drop_column('seller_otp_items', 'fullz_phone')
    op.drop_column('seller_otp_items', 'fullz_zip')
    op.drop_column('seller_otp_items', 'fullz_state')
    op.drop_column('seller_otp_items', 'fullz_city')
    op.drop_column('seller_otp_items', 'fullz_address')
    op.drop_column('seller_otp_items', 'fullz_ssn')
    op.drop_column('seller_otp_items', 'fullz_dob')
    op.drop_column('seller_otp_items', 'fullz_last_name')
    op.drop_column('seller_otp_items', 'fullz_first_name')
    op.drop_column('seller_otp_items', 'zip')
    op.drop_column('seller_otp_items', 'state')
    
    # Remove Selfreg CC fields
    op.drop_column('seller_selfreg_cc_items', 'return_days')
    op.drop_column('seller_selfreg_cc_items', 'return_item_enabled')
    op.drop_column('seller_selfreg_cc_items', 'vcc_bin')
    op.drop_column('seller_selfreg_cc_items', 'registration_date')
    
    # Remove CC NON VBV pricing
    op.drop_column('seller_cc_items', 'buyer_price_non_vbv')
    op.drop_column('seller_cc_items', 'seller_price_non_vbv')
    
    # Remove Brute Bank fields
    op.drop_column('brute_bank_items', 'has_docs')
    op.drop_column('brute_bank_items', 'additional_info')
    op.drop_column('brute_bank_items', 'zip')
    op.drop_column('brute_bank_items', 'state')
    op.drop_column('brute_bank_items', 'address')
    op.drop_column('brute_bank_items', 'holder_name')
    op.drop_column('brute_bank_items', 'routing_number')
    op.drop_column('brute_bank_items', 'account_number')
    op.drop_column('brute_bank_items', 'exact_balance')
    
    # Remove Banks section fields
    op.drop_column('seller_bank_items', 'return_days')
    op.drop_column('seller_bank_items', 'return_item_enabled')
    op.drop_column('seller_bank_items', 'phone_can_swap')
    op.drop_column('seller_bank_items', 'balance')
    op.drop_column('seller_bank_items', 'product_type')
    op.drop_column('seller_bank_items', 'bank_code')
    op.drop_column('seller_bank_items', 'category')
    
    # Rename table back
    op.rename_table('seller_bank_items', 'seller_bank_selfreg_items')
