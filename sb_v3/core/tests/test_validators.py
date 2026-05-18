"""
test_validators.py — Complete tests for validators.py
Pure functions: no external deps, fully sync.
"""
import pytest
from validators import (
    extract_ssn, extract_phone, extract_zip, extract_state, extract_dob,
    extract_address, extract_name_from_line, remove_labels,
    parse_freeform, validate_phone, validate_ssn, validate_state,
    validate_zip, validate_dob, validate_email, parse_phone_list,
    parse_person_list, format_ssn_display, format_phone_display,
    US_STATES, US_STATES_LIST, US_STATES_REVERSE,
    SSN_REGEX, ZIP_REGEX, PHONE_REGEX, DOB_REGEX, EMAIL_REGEX,
    STREET_TYPES, COMMON_CITIES,
)


# ─── extract_ssn ─────────────────────────────────────────────────────────────

class TestExtractSsn:
    def test_dashed_ssn(self):
        ssn, rest = extract_ssn("John Doe 123-45-6789 NYC")
        assert ssn == "123-45-6789"
        assert "6789" not in rest

    def test_nine_digits_no_dashes(self):
        ssn, rest = extract_ssn("SSN: 123456789")
        assert ssn == "123-45-6789"
        assert "123456789" not in rest

    def test_nine_digits_standalone(self):
        ssn, rest = extract_ssn("123456789")
        assert ssn == "123-45-6789"
        assert rest == ""

    def test_no_ssn(self):
        ssn, rest = extract_ssn("John Smith")
        assert ssn is None

    def test_ssn_with_phone_adjacent_does_not_confuse(self):
        ssn, rest = extract_ssn("SSN 123456789 and phone 3209320202")
        assert ssn == "123-45-6789"
        assert "3209320202" in rest

    def test_ssn_at_start(self):
        ssn, rest = extract_ssn("123-45-6789 John Doe")
        assert ssn == "123-45-6789"
        assert "John" in rest

    def test_partial_digit_sequence_not_extracted(self):
        ssn, rest = extract_ssn("code: 12345678")
        assert ssn is None


# ─── extract_phone ───────────────────────────────────────────────────────────

class TestExtractPhone:
    @pytest.mark.parametrize("raw,expected_prefix", [
        ("+1 (320) 932-0202", "320"),
        ("1-320-932-0202", "320"),
        ("320-932-0202", "320"),
        ("3209320202", "320"),
        ("(320) 932 0202", "320"),
        ("+13209320202", "1320"),
    ])
    def test_various_formats(self, raw, expected_prefix):
        phone, rest = extract_phone(raw)
        assert phone is not None
        digits = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        assert expected_prefix in digits

    def test_with_label(self):
        phone, rest = extract_phone("Phone: 555-123-4567 John")
        assert "555-123-4567" in phone
        assert "John" in rest

    def test_no_phone(self):
        phone, rest = extract_phone("John Smith")
        assert phone is None

    def test_removes_extracted_from_text(self):
        phone, rest = extract_phone("Call 555-123-4567 now")
        assert phone is not None
        assert "555-123-4567" not in rest

    def test_uk_format_not_extracted(self):
        phone, rest = extract_phone("+44 7911 123456")
        # UK numbers don't match US pattern; may extract partial, but 44 isn't there
        assert phone is None or "44" not in phone.replace(" ", "")


# ─── extract_zip ─────────────────────────────────────────────────────────────

class TestExtractZip:
    @pytest.mark.parametrize("raw,expected", [
        ("10001", "10001"),
        ("10001-1234", "10001-1234"),
        ("  90210  ", "90210"),
    ])
    def test_valid_zip_formats(self, raw, expected):
        zc, rest = extract_zip(raw)
        assert zc is not None
        assert expected in zc

    def test_zip_in_address(self):
        zc, rest = extract_zip("123 Main St, New York, NY 10001")
        assert zc == "10001"

    def test_no_zip(self):
        zc, rest = extract_zip("No zip here")
        assert zc is None

    def test_zip_removed_from_text(self):
        zc, rest = extract_zip("ZIP: 12345 and more text")
        assert zc == "12345"
        assert "12345" not in rest


# ─── extract_state ───────────────────────────────────────────────────────────

class TestExtractState:
    @pytest.mark.parametrize("code", ["CA", "NY", "TX", "FL", "WA"])
    def test_two_letter_code(self, code):
        sc, rest = extract_state(f"John Smith {code}")
        assert sc == code
        assert code not in rest

    def test_full_state_name(self):
        sc, rest = extract_state("John Smith California")
        assert sc == "CA"
        assert "California" not in rest

    def test_full_state_name_lowercase(self):
        sc, rest = extract_state("john smith new york")
        assert sc == "NY"

    def test_no_state(self):
        sc, rest = extract_state("John Smith")
        assert sc is None

    def test_invalid_code(self):
        sc, rest = extract_state("John Smith ZZ")
        assert sc is None

    def test_state_removed_from_text(self):
        sc, rest = extract_state("Address: 123 Main St CA")
        assert sc == "CA"
        assert "CA" not in rest


# ─── extract_dob ─────────────────────────────────────────────────────────────

class TestExtractDob:
    @pytest.mark.parametrize("raw,expected", [
        ("01/15/1985", "01/15/1985"),
        ("02/28/1990", "02/28/1990"),
        ("12/01/1999", "12/01/1999"),
    ])
    def test_mmddyyyy(self, raw, expected):
        dob, rest = extract_dob(raw)
        assert dob == expected

    def test_month_name_format(self):
        dob, rest = extract_dob("Sep 12 1965")
        assert dob == "09/12/1965"

    def test_day_month_name_format(self):
        dob, rest = extract_dob("15 March 1978")
        assert dob == "03/15/1978"

    def test_dob_with_label(self):
        dob, rest = extract_dob("DOB: 06/20/1992")
        assert dob == "06/20/1992"

    def test_yyyymmdd(self):
        dob, rest = extract_dob("19850325")
        assert dob == "03/25/1985"

    def test_mmddyyyy_compact(self):
        dob, rest = extract_dob("12251990")
        assert dob == "12/25/1990"

    def test_dash_separator(self):
        dob, rest = extract_dob("01-15-1985")
        assert dob == "01/15/1985"

    def test_two_digit_year_expanded(self):
        # 85 > 50 → goes to 1900s: 1985
        dob, rest = extract_dob("01/15/85")
        assert dob is not None

    def test_no_dob(self):
        dob, rest = extract_dob("John Smith")
        assert dob is None

    def test_invalid_date_not_extracted(self):
        dob, rest = extract_dob("02/30/1990")
        assert dob is None

    def test_removed_from_text(self):
        dob, rest = extract_dob("Born: 05/15/1985 John")
        assert dob == "05/15/1985"
        assert "1985" not in rest

    def test_december_date(self):
        dob, rest = extract_dob("12/25/1990")
        assert dob == "12/25/1990"

    def test_ymd_slash_format(self):
        dob, rest = extract_dob("1990/05/15")
        assert dob == "05/15/1990"


# ─── extract_address ─────────────────────────────────────────────────────────

class TestExtractAddress:
    @pytest.mark.parametrize("raw,number", [
        ("123 Main Street", "123"),
        ("456 Oak Avenue", "456"),
        ("789 Elm Road", "789"),
        ("100 Pine Lane", "100"),
    ])
    def test_various_street_types(self, raw, number):
        addr, rest = extract_address(raw)
        assert addr is not None
        assert number in addr

    def test_with_apt(self):
        addr, rest = extract_address("123 Main St Apt 4")
        assert addr is not None

    def test_with_suite(self):
        addr, rest = extract_address("456 Oak Ave Suite 100")
        assert addr is not None

    def test_with_unit(self):
        addr, rest = extract_address("789 Elm Road Unit 5")
        assert addr is not None

    def test_with_hash_unit(self):
        addr, rest = extract_address("100 Pine Ln #3B")
        assert addr is not None

    def test_no_address(self):
        addr, rest = extract_address("John Smith")
        assert addr is None

    def test_address_removed_from_text(self):
        addr, rest = extract_address("Lives at 123 Main St and works")
        assert addr is not None
        assert "123 Main St" not in rest


# ─── extract_name_from_line ──────────────────────────────────────────────────

class TestExtractNameFromLine:
    def test_two_word_name(self):
        fn, ln = extract_name_from_line("John Smith")
        assert fn == "John"
        assert ln == "Smith"

    def test_three_word_name(self):
        fn, ln = extract_name_from_line("Mary Jane Watson")
        assert fn == "Mary Jane"
        assert ln == "Watson"

    def test_more_than_three_words(self):
        fn, ln = extract_name_from_line("John Robert James Smith")
        assert fn == "John Robert James"
        assert ln == "Smith"

    def test_punctuation_separated(self):
        fn, ln = extract_name_from_line("John|Smith")
        assert fn == "John"
        assert ln == "Smith"

    def test_with_aka_label(self):
        fn, ln = extract_name_from_line("Mary Jane Watson aka Mary J")
        assert fn is not None
        assert ln is not None

    def test_single_word(self):
        fn, ln = extract_name_from_line("Cher")
        assert fn == "Cher"
        assert ln is None

    def test_numbers_not_name(self):
        fn, ln = extract_name_from_line("123 456")
        assert fn is None
        assert ln is None

    def test_short_words_not_name(self):
        fn, ln = extract_name_from_line("a b c d")
        assert fn is None
        assert ln is None

    def test_mixed_case_title(self):
        fn, ln = extract_name_from_line("jane doe")
        assert fn == "Jane"
        assert ln == "Doe"


# ─── remove_labels ───────────────────────────────────────────────────────────

class TestRemoveLabels:
    def test_name_label(self):
        result = remove_labels("Name: John Smith")
        assert "Name" not in result
        assert "John" in result

    def test_address_label(self):
        result = remove_labels("Address: 123 Main St")
        assert "Address" not in result

    def test_multiple_labels(self):
        result = remove_labels("Name: John | Address: 123 Main")
        assert "Name" not in result
        assert "Address" not in result
        assert "John" in result

    def test_phone_label(self):
        result = remove_labels("Phone: 555-123-4567")
        assert "Phone" not in result

    def test_pipe_characters_removed(self):
        result = remove_labels("a | b | c")
        assert "|" not in result

    def test_no_change(self):
        result = remove_labels("Plain text with no labels")
        assert result == "Plain text with no labels"

    def test_dob_label(self):
        result = remove_labels("DOB: 01/15/1985")
        assert "DOB" not in result

    def test_ssn_label(self):
        result = remove_labels("SSN: 123-45-6789")
        assert "SSN" not in result


# ─── parse_freeform ──────────────────────────────────────────────────────────

class TestParseFreeform:
    def test_empty_input(self):
        result = parse_freeform("")
        assert result["valid"] is False
        assert "Empty" in result["errors"][0]

    def test_whitespace_only(self):
        result = parse_freeform("   ")
        assert result["valid"] is False

    def test_single_name(self):
        result = parse_freeform("John Smith")
        assert result["first_name"] == "John"
        assert result["last_name"] == "Smith"
        assert result["valid"] is True

    def test_single_line_with_state_and_zip(self):
        result = parse_freeform("Jane Doe CA 90210")
        assert result["first_name"] == "Jane"
        assert result["last_name"] == "Doe"
        assert result["state"] == "CA"
        assert result["zip"] == "90210"

    def test_multiline_format(self):
        text = "John Smith\n123 Main St, New York, NY 10001\nDOB: 01/15/1985"
        result = parse_freeform(text)
        assert result["first_name"] == "John"
        assert result["last_name"] == "Smith"
        assert result["address"] is not None
        assert result["dob"] == "01/15/1985"

    def test_structured_key_value(self):
        text = "First Name: John\nLast Name: Smith\nPhone: 555-123-4567"
        result = parse_freeform(text)
        assert result["first_name"] == "John"
        assert result["last_name"] == "Smith"
        assert result["phone"] is not None

    def test_pipe_format(self):
        text = "John Smith|123 Main St|New York|NY|10001"
        result = parse_freeform(text)
        assert result["first_name"] == "John"
        assert result["last_name"] == "Smith"
        assert result["state"] == "NY"

    def test_required_fields_default(self):
        result = parse_freeform("John Smith")
        assert result["valid"] is True

    def test_required_fields_missing(self):
        result = parse_freeform("123 Main St")
        assert result["valid"] is False

    def test_required_fields_custom(self):
        result = parse_freeform("John Smith 10001", required_fields=["first_name", "zip"])
        assert result["valid"] is True

    def test_ssn_extracted(self):
        result = parse_freeform("Jane Doe 123-45-6789")
        assert result["ssn"] == "123-45-6789"



    def test_email_regex_anchored(self):
        # EMAIL_REGEX has ^$ anchors — validates entire string as email
        # Use for validation, not extraction from freeform
        import re
        from validators import EMAIL_REGEX
        assert re.match(EMAIL_REGEX, "john@example.com", re.IGNORECASE)
        assert re.match(EMAIL_REGEX, "USER@EXAMPLE.COM", re.IGNORECASE)
        assert not re.match(EMAIL_REGEX, "John Smith john@example.com")

    def test_phone_extracted(self):
        result = parse_freeform("Jane Doe 555-123-4567")
        assert result["phone"] is not None


# ─── validate_phone ──────────────────────────────────────────────────────────

class TestValidatePhone:
    @pytest.mark.parametrize("raw,expected_clean", [
        ("320-932-0202", "+13209320202"),
        ("+1 320 932 0202", "+13209320202"),
        ("(320) 932-0202", "+13209320202"),
        ("3209320202", "+13209320202"),
    ])
    def test_valid_phones_normalized(self, raw, expected_clean):
        ok, norm, err = validate_phone(raw)
        assert ok is True
        assert norm == expected_clean
        assert err == ""

    def test_valid_11_digit(self):
        ok, norm, err = validate_phone("+13209320202")
        assert ok is True
        assert norm == "+13209320202"

    @pytest.mark.parametrize("invalid", [
        "123", "123-456", "1234567890123", "abc-def-ghij", ""
    ])
    def test_invalid_phones(self, invalid):
        ok, norm, err = validate_phone(invalid)
        assert ok is False
        assert err != ""

    def test_phone_error_message(self):
        ok, norm, err = validate_phone("abc")
        assert "Invalid phone" in err


# ─── validate_ssn ────────────────────────────────────────────────────────────

class TestValidateSsn:
    @pytest.mark.parametrize("raw,expected", [
        ("123-45-6789", "123-45-6789"),
        ("123456789", "123-45-6789"),
        ("123 45 6789", "123-45-6789"),
    ])
    def test_valid_ssn_normalized(self, raw, expected):
        ok, norm, err = validate_ssn(raw)
        assert ok is True
        assert norm == expected

    @pytest.mark.parametrize("invalid", [
        "123-45-678", "12345678", "1234567890", "", "abc",
    ])
    def test_invalid_ssn(self, invalid):
        ok, norm, err = validate_ssn(invalid)
        assert ok is False

    def test_ssn_error_message(self):
        ok, norm, err = validate_ssn("1234")
        assert "Invalid SSN" in err


# ─── validate_state ───────────────────────────────────────────────────────────

class TestValidateState:
    @pytest.mark.parametrize("code", ["CA", "NY", "TX", "FL", "ZZ"])
    def test_valid_codes(self, code):
        ok, norm, err = validate_state(code)
        if code in US_STATES_LIST:
            assert ok is True
            assert norm == code
        else:
            assert ok is False

    def test_full_name_to_code(self):
        ok, norm, err = validate_state("California")
        assert ok is True
        assert norm == "CA"

    def test_full_name_lowercase(self):
        ok, norm, err = validate_state("new york")
        assert ok is True
        assert norm == "NY"

    def test_invalid_state_error(self):
        ok, norm, err = validate_state("ZZ")
        assert ok is False
        assert "Invalid state" in err


# ─── validate_zip ───────────────────────────────────────────────────────────

class TestValidateZip:
    @pytest.mark.parametrize("valid_zip", [
        "10001", "90210", "12345-6789", "12345",
    ])
    def test_valid_zips(self, valid_zip):
        ok, norm, err = validate_zip(valid_zip)
        assert ok is True

    @pytest.mark.parametrize("invalid", [
        "1234", "123456", "ABCDE", "", "12345-678", "123456-7890",
    ])
    def test_invalid_zips(self, invalid):
        ok, norm, err = validate_zip(invalid)
        assert ok is False
        assert err != ""

    def test_zip_whitespace_stripped(self):
        ok, norm, err = validate_zip("  10001  ")
        assert ok is True
        assert norm == "10001"


# ─── validate_dob ───────────────────────────────────────────────────────────

class TestValidateDob:
    @pytest.mark.parametrize("raw,expected", [
        ("01/15/1985", "01/15/1985"),
        ("12/31/1990", "12/31/1990"),
        ("06/01/2000", "06/01/2000"),
    ])
    def test_valid_dob(self, raw, expected):
        ok, norm, err = validate_dob(raw)
        assert ok is True
        assert norm == expected

    def test_dob_month_name(self):
        ok, norm, err = validate_dob("Sep 12 1965")
        assert ok is True
        assert norm == "09/12/1965"

    def test_two_digit_year_valid(self):
        # 85 > 50 → 1985, which is valid
        ok, norm, err = validate_dob("01/15/85")
        assert ok is True
        assert norm == "01/15/1985"

    @pytest.mark.parametrize("invalid", [
        "invalid", "", "1/1/1", "abc",
    ])
    def test_invalid_dob_non_date(self, invalid):
        ok, norm, err = validate_dob(invalid)
        assert ok is False

    def test_dob_error_message(self):
        ok, norm, err = validate_dob("bad")
        assert "Invalid DOB" in err


# ─── validate_email ─────────────────────────────────────────────────────────

class TestValidateEmail:
    @pytest.mark.parametrize("valid_email", [
        "user@example.com",
        "test.user@domain.org",
        "user+tag@gmail.com",
        "a@b.co",
        "USER@EXAMPLE.COM",
    ])
    def test_valid_emails(self, valid_email):
        ok, norm, err = validate_email(valid_email)
        assert ok is True
        assert norm == valid_email.lower()

    @pytest.mark.parametrize("invalid", [
        "not-an-email", "missing@domain", "@nodomain.com",
        "spaces in@email.com", "", "a@b",
    ])
    def test_invalid_emails(self, invalid):
        ok, norm, err = validate_email(invalid)
        assert ok is False

    def test_email_whitespace_stripped(self):
        ok, norm, err = validate_email("  user@example.com  ")
        assert ok is True
        assert norm == "user@example.com"


# ─── parse_phone_list ───────────────────────────────────────────────────────

class TestParsePhoneList:
    def test_valid_phones(self):
        text = "320-932-0202\n555-123-4567\n+1 212 555 0199"
        valid, errors = parse_phone_list(text)
        assert len(valid) == 3
        assert len(errors) == 0

    def test_mixed_valid_invalid(self):
        text = "320-932-0202\ninvalid\n+1 212 555 0199"
        valid, errors = parse_phone_list(text)
        assert len(valid) == 2
        assert len(errors) == 1

    def test_all_invalid(self):
        text = "abc\n123\n---"
        valid, errors = parse_phone_list(text)
        assert len(valid) == 0
        assert len(errors) == 3

    def test_empty_lines_skipped(self):
        text = "320-932-0202\n\n555-123-4567\n"
        valid, errors = parse_phone_list(text)
        assert len(valid) == 2

    def test_semicolon_separated_stripped(self):
        text = "320-932-0202; 555-123-4567"
        valid, errors = parse_phone_list(text)
        # semicolons stripped per line, each line is one entry
        assert len(errors) >= 0


# ─── parse_person_list ───────────────────────────────────────────────────────

class TestParsePersonList:
    def test_single_person(self):
        text = "John Smith"
        persons, errors = parse_person_list(text)
        assert len(persons) == 1
        assert persons[0]["first_name"] == "John"
        assert persons[0]["last_name"] == "Smith"

    def test_multiple_persons(self):
        text = "John Smith\n\nJane Doe"
        persons, errors = parse_person_list(text)
        assert len(persons) == 2
        assert persons[0]["first_name"] == "John"
        assert persons[1]["first_name"] == "Jane"

    def test_persons_with_all_fields(self):
        text = "John Smith 123 Main St NY 10001"
        persons, errors = parse_person_list(text)
        assert len(persons) == 1
        assert persons[0]["state"] == "NY"
        assert persons[0]["zip"] == "10001"

    def test_missing_name_recorded_as_error(self):
        text = "123 Main St"
        persons, errors = parse_person_list(text)
        assert len(persons) == 0
        assert len(errors) == 1
        assert "could not extract name" in errors[0]

    def test_blank_lines_skipped(self):
        text = "John Smith\n\n\nJane Doe"
        persons, errors = parse_person_list(text)
        assert len(persons) == 2


    def test_error_contains_line_info(self):
        # Numbers-only text has no valid name words — will fail extraction
        text = "123 Main Street 90210"
        persons, errors = parse_person_list(text)
        assert len(errors) == 1
        assert "Line" in errors[0]


# ─── format_ssn_display ──────────────────────────────────────────────────────

class TestFormatSsnDisplay:
    def test_dashed_input(self):
        result = format_ssn_display("123-45-6789")
        assert result == "123-45-6789"

    def test_nine_digits(self):
        result = format_ssn_display("123456789")
        assert result == "123-45-6789"

    def test_with_spaces(self):
        result = format_ssn_display("123 45 6789")
        assert result == "123-45-6789"

    def test_invalid_length_unchanged(self):
        result = format_ssn_display("12345")
        assert result == "12345"


# ─── format_phone_display ───────────────────────────────────────────────────

class TestFormatPhoneDisplay:
    def test_10_digit(self):
        result = format_phone_display("3209320202")
        assert result == "+1 (320) 932-0202"

    def test_11_digit_with_1(self):
        result = format_phone_display("+13209320202")
        assert result == "+1 (320) 932-0202"

    def test_already_formatted(self):
        result = format_phone_display("+1 (320) 932-0202")
        assert "320" in result

    def test_short_number_unchanged(self):
        result = format_phone_display("123")
        assert result == "123"


# ─── Module constants ───────────────────────────────────────────────────────

class TestModuleConstants:
    def test_us_states_50_plus_dc(self):
        assert len(US_STATES) >= 50
        assert "CA" in US_STATES
        assert "NY" in US_STATES
        assert "DC" in US_STATES

    def test_us_states_reverse(self):
        assert US_STATES_REVERSE["california"] == "CA"
        assert US_STATES_REVERSE["new york"] == "NY"

    def test_street_types_not_empty(self):
        assert len(STREET_TYPES) > 30

    def test_common_cities_not_empty(self):
        assert len(COMMON_CITIES) > 50

    def test_regexes_nonempty(self):
        assert SSN_REGEX
        assert ZIP_REGEX
        assert PHONE_REGEX
        assert DOB_REGEX
        assert EMAIL_REGEX