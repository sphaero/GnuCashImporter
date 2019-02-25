from gnucash import Session, Account, Transaction, Split, GncNumeric, gnucash_core
import mt940
from mt940 import MT940
from decimal import Decimal
import sys

import argparse

parser = argparse.ArgumentParser(description='Import a MT940 file into Gnucash and match Gnucash accounts to transactions.')
parser.add_argument('mt940', type=str, help='mt940 file to import from')
parser.add_argument('gnucash', type=str, help='gnucash file to import to')

args = parser.parse_args()
print(("Parsing mt940 file {0} and Gnucash file {1}".format(args.mt940, args.gnucash)))

def gnc_get_child_accounts_dict(account, d=None):
    """
    Returns a list of all child accounts of account
    """
    if not d:
        d={}
    children = account.get_children()
    if children:
        for acc in account.get_children():
            d = gnc_get_child_accounts_dict(acc, d)
    else:
        d[account.name] = account
    return d

def gnc_numeric_from_decimal(decimal_value):
    """
    Returns a GncNumeric of a decimal value
    """
    sign, digits, exponent = decimal_value.as_tuple()
 
    # convert decimal digits to a fractional numerator
    # equivlent to
    # numerator = int(''.join(digits))
    # but without the wated conversion to string and back,
    # this is probably the same algorithm int() uses
    numerator = 0
    TEN = int(Decimal(0).radix()) # this is always 10
    numerator_place_value = 1
    # add each digit to the final value multiplied by the place value
    # from least significant to most sigificant
    for i in range(len(digits)-1,-1,-1):
        numerator += digits[i] * numerator_place_value
        numerator_place_value *= TEN

    if decimal_value.is_signed():
        numerator = -numerator

    # if the exponent is negative, we use it to set the denominator
    if exponent < 0 :
        denominator = TEN ** (-exponent)
        # if the exponent isn't negative, we bump up the numerator
        # and set the denominator to 1
    else:
        numerator *= TEN ** exponent
        denominator = 1

    return GncNumeric(numerator, denominator)

def _get_leave_account(acc, acc_dict):
    children = acc.get_children()
    print(("boe", children))
    if children:
        print("yesy")
        for a in children():
            print(("huh", a.name))
            acc_dict = _get_leave_account(a, acc_dict)
    else:
        acc_dict[acc.name] = acc
    return acc_dict    

try:
    session = Session(args.gnucash)
except gnucash_core.GnuCashBackendException as e:
    print(e)
    sys.exit(1)

book = session.get_book()
currency = book.get_table().lookup("CURRENCY", "EUR")
ing = book.get_root_account().get_children()[0].get_children()[0].get_children()[0]     
root_acc = book.get_root_account()

# dict containing all expenses accounts (flat tree)
child_accounts = gnc_get_child_accounts_dict(root_acc)

#print(gnc_get_child_accounts_dict(expenses))

mt = MT940(args.mt940)
# this should usually be one statement

transacts = []

def gen_description(description):
    description = mt940.ing_description(description)
    ret = ""
    if description.get('remi'):
        ret += description['remi']['remittance_info']
    if description.get('cntp'):
        if len(ret): ret+= " "
        ret += description['cntp'].get('name', '')
    return ret

for statement in mt.statements:
    #print(statement.information)
    for transaction in statement.transactions:
        #print(transaction.booking, transaction.amount, transaction.reference, transaction.account, transaction.description)
        t = {}
        t['date'] = transaction.booking
        t['amount'] = transaction.amount
        t['desc'] = gen_description(str(transaction.description).replace('\n',''))
        t['account'] = ""
        transacts.append(t)

from . import gnc_urw

try:
    print((gnc_urw.gnc_urw_edit(transacts, child_accounts)))
    print(transacts)

    for t in transacts:
        #print gnc_numeric_from_decimal(tamount)
        
        trans = Transaction(book)
        trans.BeginEdit()
        trans.SetCurrency(currency)
        split1 = Split(book)
        split1.SetValue(gnc_numeric_from_decimal(t['amount']))
        split1.SetAccount(ing)
        split1.SetParent(trans)

        split2 = Split(book)
        split2.SetValue(gnc_numeric_from_decimal(t['amount']).neg())
        split2.SetAccount(t['account'])
        split2.SetParent(trans)
            
        trans.SetDescription(t['desc'])
        tdate = t['date']
        trans.SetDate(tdate.day, tdate.month, tdate.year)
        trans.CommitEdit()
finally:
    session.save()
    session.end()
    session.destroy()

