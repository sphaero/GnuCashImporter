import urwid
import sys
import io
import time
from decimal import Decimal

transactions = [{'desc':'1'},{'desc':'2'},{'desc':'3'},{'desc':'4'},{'desc':'5'},{'desc':'6'},{'desc':'7'}]
options = {'bla': 'bla', 'cavia':'cavia', 'kantoor':'kantoor', 'kantine':'kantine'}

class UrwStdWriter(io.TextIOWrapper):

    def __init__(self, *args, **kwargs):
        self.wgt = urwid.Text("")
        self.oldout = sys.stdout
        super(UrwStdWriter, self).__init__(io.BytesIO(), sys.stdout.encoding, *args, **kwargs)
        self.maxrows = 5
        
    def capture_stdout(self):
        self.oldout = sys.stdout
        sys.stdout = self
        
    def release_stdout(self):
        sys.stdout = self.oldout
    
    def __del__(self):
        self.release_stdout()

    def write(self, data):
        #if self.wgt.get_text()[0].count('\n') > self.wgt.rows() and len(self.wgt.get_text()):
        if self.wgt.get_text()[0].count('\n') > self.maxrows:
            cuttxt = self.wgt.get_text()[0].split('\n')[1:]
            self.wgt.set_text("%s%s" %(self.wgt.get_text()[0].split('\n',1)[1], data))
        else:
            self.wgt.set_text("%s%s" %(self.wgt.get_text()[0], data))

    def get_widget(self):
        return self.wgt


class EditCompletion(urwid.Edit):
    
    def __init__(self, options, *args, **kwargs):
        self.options = options
        super(EditCompletion, self).__init__(*args, **kwargs)

    def keypress(self, size, key):
        p = self.edit_pos
        super(EditCompletion, self).keypress(size, key)
        
        if self.valid_char(key):
            p = self.edit_pos
            cur = self.get_edit_text()
            if len(cur) and p:
                for o in self.options:
                    if o.startswith(cur[:p]):
                        self.set_edit_text(o)
                        break
            if self.get_edit_text() in self.options:
                return key
        else:
        #elif key=="tab" and self.allow_tab:
        #    key = " "*(8-(self.edit_pos%8))
        #    self.insert_text(key)
            return key

class FloatEdit(urwid.Edit):
    """Edit widget for float values"""

    def valid_char(self, ch):
        """
        Return true for decimal digits.
        """
        if self.get_edit_text().count('.') < 1:
            return len(ch)==1 and ch in ".0123456789"
        return len(ch)==1 and ch in "0123456789"

    def __init__(self,caption="",default=None):
        """
        caption -- caption markup
        default -- default edit value

        >>> IntEdit(u"", 42)
        <IntEdit selectable flow widget '42' edit_pos=2>
        """
        if default is not None: val = str(default)
        else: val = ""
        self.__super.__init__(caption,val)

    def keypress(self, size, key):
        """
        Handle editing keystrokes.  Remove leading zeros.

        >>> e, size = FloatEdit(u"", 500.2), (10,)
        >>> e.keypress(size, 'home')
        >>> e.keypress(size, 'delete')
        >>> print e.edit_text
                002
        >>> e.keypress(size, 'end')
        >>> print e.edit_text
        2
        """
        (maxcol,) = size
        unhandled = super(FloatEdit, self).keypress(size, key)

        if not unhandled:
            # trim leading zeros
            while self.edit_pos > 0 and self.edit_text[:1] == "0":
                self.set_edit_pos( self.edit_pos - 1)
                self.set_edit_text(self.edit_text[1:])
                if self.edit_text[0] == '.':
                    self.set_edit_text("0"+self.edit_text)

        return unhandled

    def value(self):
        """
        Return the numeric value of self.edit_text.

        >>> e, size = IntEdit(), (10,)
        >>> e.keypress(size, '5')
        >>> e.keypress(size, '1')
        >>> e.value() == 51
        True
        """
        if self.edit_text:
            return float(self.edit_text)
        else:
            return 0.0

class TransactionListBox(urwid.ListBox):
    def __init__(self, transactions, account_options, *args, **kwargs):
        tws = []
        for t in transactions:
            tws.append(urwid.Pile(
                (
                    urwid.Text(('title transaction', "[{0}]{1}".format(t.get('amount', 0), t['desc']))), 
                    EditCompletion(account_options), 
                    FloatEdit(caption='BTW: ', default=str((t.get('amount',Decimal(0.0))/121*21).quantize(Decimal('.01'))))
                )
            ))
        #urwid.Pile()
        body = urwid.SimpleFocusListWalker(tws)
        
        super(TransactionListBox, self).__init__(body)
        
    #def keypress(self, size, key):
    #    if key != 'enter':
    #        return super(TransactionListBox, self).keypress(size, key)
    #    self.original_widget = urwid.Text(
    #        u"Nice to meet you,\n%s.\n\nPress Q to exit." %
    #        edit.edit_text)

palette = [
    (None,  'light gray', 'black'),
    ('heading', 'black', 'light gray'),
    ('line', 'black', 'light gray'),
    ('options', 'dark gray', 'black'),
    ('focus heading', 'white', 'dark red'),
    ('focus line', 'black', 'dark red'),
    ('focus options', 'black', 'light gray'),
    ('selected', 'light gray', 'dark blue'),
    ('title transaction', 'white', 'dark blue')]
        
def on_cancel_clicked(button):
    raise urwid.ExitMainLoop()

def gnc_urw_edit(transactions, options):

    def unhandled_key(key):
        if key == 'esc':
            raise urwid.ExitMainLoop()
        elif key == 'f2':
            on_save_clicked(None)

    def on_save_clicked(button):
        count = 0
        for pile in tlb.original_widget.body:
            acc_name = pile.contents[1][0].get_edit_text()
            try:
                transactions[count]['account'] = options[acc_name]
            except Exception as e:
                print("Can't match accounts, please fix: %s" %e)
                break
            tax = pile.contents[2][0].value()
            try:
                transactions[count]['tax'] = tax
            except Exception as e:
                print("Can't get text value, please fix row: %s" %e)
                break
            else:
                count += 1

        print count, len(transactions)
        if count == len(transactions):
            out.release_stdout()
            raise urwid.ExitMainLoop()
        else:
            print("ERROR: not all transactions are matched")

    cancel_b = urwid.Button('ESC:Cancel')
    save_b = urwid.Button('F2:Save&Exit')
    urwid.connect_signal(save_b, 'click', on_save_clicked)
    urwid.connect_signal(cancel_b, 'click', on_cancel_clicked)
    footer = urwid.AttrMap(urwid.Columns(((18, save_b), (16,cancel_b)),dividechars=5), 'heading')
    header = urwid.AttrMap(urwid.Text("Edit transactions"), 'heading')

    tlb = urwid.AttrMap(TransactionListBox(transactions, options.keys()), 'selected')
    acc_options = urwid.AttrMap(urwid.LineBox(urwid.Text("\n".join(options)), title='options'), 'focus options')
    out = UrwStdWriter()

    debug = urwid.Filler(urwid.LineBox(out.get_widget(), title='debug'), height='flow', min_height=10)
    frame = urwid.Frame(urwid.Columns((tlb, (20, urwid.Filler(acc_options)))), header=header, footer=footer)
    loop = urwid.MainLoop(urwid.Pile((('weight', 10, frame), (10, debug))), unhandled_input=unhandled_key, palette=palette)
    out.capture_stdout()
    loop.run()
    print("urwid finished")
    return transactions

if __name__ == '__main__':
    gnc_urw_edit(transactions, options)
