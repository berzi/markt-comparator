"""MarktComparator compares products and markets to return what market is best to buy what products.

This is the GUI module, built with wxPython.

Features:
    Native look.
    A list to display and allow selection of all the unique products.
    A text input to search for specific products.
    A multi-line label to display the output, which is triggered on selection. Format:
        [Product] is sold in:
        - [Market1] for [price]€
        - [Market2] for [price]€
        ...
    A button to copy the output to the clipboard.
    Buttons to handle the data:
        New item.
        Edit selection.
        Delete selection.
    Keyboard shortcuts for all buttons.
"""

from mCbackend import *
import wx
import re


# Define reusable sizer flags for use with layouts:
size_option_FIT = wx.SizerFlags(proportion=1)
size_option_FIT.Align(wx.ALIGN_CENTRE)  # Align elements to the container's centre.
size_option_FIT.Expand()  # Fit all the space in their container.

size_option_CTR = wx.SizerFlags(proportion=1)
size_option_CTR.Align(wx.ALIGN_CENTRE)  # Align elements to the container's centre.


class OutputLabel(wx.StaticText):
    """Singleton for a label used for output, intended to change its contents when needed."""
    def __init__(self, parent):
        """Initialise the label with the default values and a default text depending on localisation."""
        super().__init__(parent=parent, style=wx.ALIGN_LEFT, label=loc.lan["DefaultOutput"])


class RestartDialog(wx.Dialog):
    """Dialog to instruct the user to restart the program for language changes to take effect."""
    def __init__(self, parent):
        super().__init__(parent=parent, title=loc.lan["RestartDialog"],
                         style=wx.DEFAULT_DIALOG_STYLE)

        dialog_box = wx.BoxSizer(orient=wx.VERTICAL)  # Make a box to hold the dialog elements.

        instructions_label = wx.StaticText(parent=self, label=loc.lan["RestartInstructions"])
        dialog_box.Add(instructions_label, size_option_CTR)

        button_sizer = self.CreateStdDialogButtonSizer(wx.OK)  # Add default button.

        dialog_sizer = wx.BoxSizer(orient=wx.VERTICAL)
        dialog_sizer.Add(dialog_box)
        dialog_sizer.Add(button_sizer)
        # Add all elements to a sizer to group them together.

        self.SetSizer(dialog_sizer)
        self.Layout()
        self.CentreOnScreen()  # TODO: Make elements properly centred.


class LanguageSelector(wx.Choice):
    """Singleton for the creation of a language selector."""
    def __init__(self, parent):
        """Create a language selector, default to current language and bind options to localisation methods."""
        super().__init__(parent=parent, choices=self.list_available_languages())

        self.SetSelection(self.FindString(loc.o))

        self.Bind(wx.EVT_CHOICE, self.on_choice)

    def on_choice(self, event):
        selection = self.GetString(self.GetSelection())
        loc.change(selection)
        restart_dialog = RestartDialog(parent=self)
        restart_dialog.ShowModal()
        event.Skip()

    @staticmethod
    def list_available_languages() -> list:
        """Return a list of available localisation languages.

        Returns:
             A list of strings containing the names of available languages.
        """

        available_languages = []

        for language in loc.la:
            if language != "selected":
                available_languages.append(language)

        return available_languages


class ProductList(wx.ListBox):
    """Class for the creation of a listbox to hold all product names."""
    def __init__(self, parent):
        """Create a product list, populate it and bind it to the output label."""
        super().__init__(parent=parent,
                         style=wx.LB_SINGLE | wx.LB_ALWAYS_SB | wx.LB_SORT,
                         choices=self.create_product_list())
        self.SetSelection(0)

    def on_selection_change(self):
        """When a product is selected, catch selection and format a string to feed to output."""
        try:
            selected_product = self.GetString(self.GetSelection())
        except AssertionError:
            selected_product = ""

        if selected_product == "":
            output = loc.lan["DefaultOutput"]  # Output default if selection is invalid.
        else:
            found_in = find_product(selected_product)  # Get list of viable markets and prices for product.
            if found_in is []:
                output = loc.lan["NoProducts"]  # Output default if none found.
            else:
                if len(found_in) == 1:
                    output = "{product} {text} {market} {preposition} {price:0.02f}€".\
                        format(product=selected_product,
                               market=found_in[0][0],
                               price=found_in[0][1],
                               text=loc.lan["OnlyFound"],
                               preposition=loc.lan["PricePreposition"])
                else:
                    computed = ""
                    for market, price in found_in:
                        computed += "\n- {market}\t\t{preposition}\t{price:0.02f}€".\
                            format(market=market,
                                   price=price,
                                   preposition=loc.lan["PricePreposition"])
                    output = "{product} {text}:"\
                             .format(product=selected_product,
                                     text=loc.lan["FoundIn"]) + computed
                    # Compile a list of options if more than one is available.

        return output  # Return the output.

    def repopulate(self):
        """Repopulates the product list from scratch."""
        self.Set(self.create_product_list())

    @staticmethod
    def create_product_list() -> List[str]:
        """Populate the product list in the main window.

        Called when loading the product list and when updating it after the user modifies the content.

        Returns:
            A list of strings containing the product names.
            A list containing the default output if no products are found.
        """

        list_of_products = list_products()

        if list_of_products:
            return list_of_products
        else:
            return [loc.lan["NoProducts"]]


class EditDialog(wx.Dialog):
    """Class for a dialog to allow the user to edit an existing product."""
    def __init__(self, parent, in_markets, product):
        """Initialise the dialog with data from the current selection."""
        super().__init__(parent=parent,
                         title=loc.lan["EditDialog"],
                         style=wx.DEFAULT_DIALOG_STYLE)

        self.product = product  # Set product name as attribute for later use.

        self.dialog_box = wx.BoxSizer(orient=wx.VERTICAL)  # Make a box to hold the dialog elements.

        instructions_label = wx.StaticText(parent=self,
                                           label="{text} \"{product}\":".format(text=loc.lan["EditInstructions"],
                                                                                product=self.product))

        self.dialog_box.Add(instructions_label, size_option_CTR)
        # Write instructions for the user depending on language.

        name_box = wx.BoxSizer(orient=wx.HORIZONTAL)

        self.product_name = wx.TextCtrl(parent=self, value=self.product)
        self.product_name.Bind(wx.EVT_TEXT, self.validate_name)

        product_name_label = wx.StaticText(parent=self, label=loc.lan["ProductName"])

        self.restore_name = wx.Button(parent=self, label=loc.lan["Restore"])
        self.restore_name.Bind(wx.EVT_BUTTON, self.on_restore_name)
        self.restore_name.Disable()  # Disabled by default. Will be enabled by user input.

        name_box.Add(product_name_label)
        name_box.AddSpacer(5)
        name_box.Add(self.product_name)
        name_box.AddSpacer(5)
        name_box.Add(self.restore_name)
        self.dialog_box.Add(name_box)
        # Add a name input.

        market_box = wx.BoxSizer(orient=wx.HORIZONTAL)

        self.market_list = wx.ListBox(parent=self,
                                      style=wx.LB_SINGLE | wx.LB_ALWAYS_SB,
                                      choices=["{market}: {price:0.02f}€".format(market=market[0],
                                                                                 price=market[1])
                                               for market in in_markets])
        self.market_list.SetSelection(0)

        market_box.AddSpacer(10)
        market_box.Add(self.market_list)
        # Add a list of markets and prices the product appears in.

        self.market_remove = wx.Button(parent=self, label=loc.lan["Remove"])
        self.market_remove.Bind(wx.EVT_BUTTON, self.on_remove_market)
        if self.market_list.GetCount() < 2:
            self.market_remove.Disable()  # If there's fewer than 2 markets, disable the remove button.

        market_box.AddSpacer(5)
        market_box.Add(self.market_remove, wx.ALIGN_TOP)
        self.dialog_box.Add(market_box)
        # Make a remove button to delete selected market.

        market_add = wx.BoxSizer(orient=wx.HORIZONTAL)

        market_name_label = wx.StaticText(parent=self, label=loc.lan["Market"])

        self.market_name = wx.TextCtrl(parent=self)
        self.market_name.Bind(wx.EVT_TEXT, self.validate_new_market)

        market_middle_label = wx.StaticText(parent=self, label=loc.lan["PricePreposition"])

        self.market_price = wx.TextCtrl(parent=self, style=wx.TE_RIGHT)
        self.market_price.Bind(wx.EVT_TEXT, self.validate_new_market)

        market_price_label = wx.StaticText(parent=self, label="€")

        market_add.Add(market_name_label)
        market_add.AddSpacer(5)
        market_add.Add(self.market_name)
        market_add.AddSpacer(5)
        market_add.Add(market_middle_label)
        market_add.AddSpacer(5)
        market_add.Add(self.market_price)
        market_add.Add(market_price_label)
        self.dialog_box.AddSpacer(5)
        self.dialog_box.Add(market_add)
        # Make a form to add a new market.

        self.add_market = wx.Button(parent=self, label=loc.lan["AddMarket"])
        self.add_market.Bind(wx.EVT_BUTTON, self.on_add_market)
        self.add_market.Disable()  # Disabled by default. Enabled when input is detected as valid.

        self.dialog_box.AddSpacer(5)
        self.dialog_box.Add(self.add_market)
        # Make a button to insert the product into new market.

        button_sizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)  # Add default buttons.
        for item in button_sizer.GetChildren():
            if item.Window and item.Window.GetLabel() == "Cancel":
                item.Window.SetLabel(loc.lan["Cancel"])
                # Convoluted way to translate the Cancel button because wxPython makes it hard to get it.
            if item.Window and item.Window.GetLabel() == "OK":
                self.OK_button = item.Window  # Catch OK button for use with validators.

        dialog_sizer = wx.BoxSizer(orient=wx.VERTICAL)
        dialog_sizer.Add(self.dialog_box)
        dialog_sizer.AddSpacer(15)
        dialog_sizer.Add(button_sizer)
        # Add all elements to a sizer to group them together.

        self.SetSizer(dialog_sizer)
        self.Layout()
        self.CentreOnScreen()  # TODO: Make elements properly centred.

    def on_restore_name(self, event):
        """Restores the product name field to its original value when the user clicks the restore button."""
        self.product_name.SetValue(self.product)  # Reset the name field to the original name.
        self.restore_name.Disable()  # Disable the restore button (will be re-enabled on change).

        event.Skip()

    def on_remove_market(self, event):
        """Remove selected market from the list when the user clicks the appropriate button.

        The list will be re-read when the edit dialog is accepted and missing markets will be eliminated.
        If there is only one item on the list, the button will be disabled.
        """

        self.market_list.Delete(self.market_list.GetSelection())  # Delete selected market from the list.
        if self.market_list.GetCount() < 2:
            self.market_remove.Disable()  # If there's now fewer than 2 markets in the list, disable the remove button.

        event.Skip()

    def on_add_market(self, event):
        """Add a market to the list following the data currently in the form, then empty the form.

        The list will be re-read when the edit dialog is accepted and additional markets will be added.
        The remove market button will be re-enabled, in case it was disabled.
        """

        clean_name = self.market_name.Value.strip()
        clean_price = float(re.sub(",", ".", self.market_price.Value.strip()))

        self.market_list.Insert("{market}: {price:0.02f}€".format(market=clean_name,
                                                                  price=clean_price),
                                self.market_list.GetCount())
        # Insert the new market with the entered data.

        self.market_name.Clear()
        self.market_price.Clear()
        # Clear the fields to facilitate a new entry.

        if self.market_list.GetCount() > 1 and not self.market_remove.IsEnabled():
            self.market_remove.Enable()
        # If there's now more than one market on the list, enable the remove market button.

        event.Skip()

    def validate_name(self, event):
        """Validate the input when the user enters a new product name and en- or disable entering accordingly.

        Invalid fields are signalled by their border becoming red.
        A valid name does not contain only numbers and cannot contain symbols except - and ().
        """

        self.restore_name.Enable()  # In any case, since the input has changed, re-enable the restore button.
        is_valid = False  # By default, input is not valid.
        if re.fullmatch("(?!^[\d ()]+$)^^[^()][ \w()]+$", self.product_name.Value.strip()):
            is_valid = True

        if not is_valid:
            self.OK_button.Disable()
            self.product_name.SetBackgroundColour(wx.Colour(red=255, green=150, blue=150, alpha=100))
            self.product_name.Refresh()
        else:
            self.OK_button.Enable()
            self.product_name.SetBackgroundColour(wx.NullColour)
            self.product_name.Refresh()

        event.Skip()

    def validate_new_market(self, event):
        """Validate the input when the user enters a new market and en- or disable entering accordingly.

        Invalid fields are signalled by their background becoming reddish.
        A valid name cannot contain only numbers and can only contain - as a symbol.
        A valid price only contains numbers and no more than one decimal separator, either . or ,.
        """

        is_name_valid = False  # By default, input is not valid.
        is_price_valid = False  # By default, input is not valid.

        if re.fullmatch("(?!^[\d ()]+$)^^[^()][ \w()]+$", self.market_name.Value.strip()):
            is_name_valid = True

        if re.fullmatch("^\d{1,3}([,.]\d+)?$", self.market_price.Value.strip()):
            is_price_valid = True

        if not is_name_valid:
            self.add_market.Disable()
            self.market_name.SetBackgroundColour(wx.Colour(red=255, green=150, blue=150, alpha=100))
            self.market_name.Refresh()
        else:
            self.market_name.SetBackgroundColour(wx.NullColour)
            self.market_name.Refresh()

        if not is_price_valid:
            self.add_market.Disable()
            self.market_price.SetBackgroundColour(wx.Colour(red=255, green=150, blue=150, alpha=100))
            self.market_price.Refresh()
        else:
            self.market_price.SetBackgroundColour(wx.NullColour)
            self.market_price.Refresh()

        if is_name_valid and is_price_valid:
            self.add_market.Enable()

        event.Skip()


class NewDialog(wx.Dialog):
    """Class for a dialog to allow the user to enter a new product."""
    def __init__(self, parent):
        """Initialise the dialog with empty fields."""
        super().__init__(parent=parent,
                         title=loc.lan["NewDialog"],
                         style=wx.DEFAULT_DIALOG_STYLE)

        self.name_is_valid = False
        self.markets_are_valid = False
        # Prepare values for cross-validation. Invalid by default.

        self.dialog_box = wx.BoxSizer(orient=wx.VERTICAL)  # Make a box to hold the dialog elements.

        instructions_label = wx.StaticText(parent=self, label="{text}:".format(text=loc.lan["NewInstructions"]))

        self.dialog_box.Add(instructions_label, size_option_CTR)
        # Write instructions for the user depending on language.

        name_box = wx.BoxSizer(orient=wx.HORIZONTAL)

        self.product_name = wx.TextCtrl(parent=self)
        self.product_name.Bind(wx.EVT_TEXT, self.validate_name)

        product_name_label = wx.StaticText(parent=self, label=loc.lan["ProductName"])

        self.reset_name = wx.Button(parent=self, label="Reset")
        self.reset_name.Bind(wx.EVT_BUTTON, self.on_reset_name)
        self.reset_name.Disable()  # Disabled by default. Will be enabled by user input.

        name_box.Add(product_name_label)
        name_box.AddSpacer(5)
        name_box.Add(self.product_name)
        name_box.AddSpacer(5)
        name_box.Add(self.reset_name)
        self.dialog_box.Add(name_box)
        # Add a name input.

        market_box = wx.BoxSizer(orient=wx.HORIZONTAL)

        self.market_list = wx.ListBox(parent=self,
                                      style=wx.LB_SINGLE | wx.LB_ALWAYS_SB,
                                      choices=[])

        market_box.AddSpacer(10)
        market_box.Add(self.market_list)
        # Add a list to hold the markets and prices the product should have.

        self.market_remove = wx.Button(parent=self, label=loc.lan["Remove"])
        self.market_remove.Bind(wx.EVT_BUTTON, self.on_remove_market)
        self.market_remove.Disable()  # Disabled by default. Will be enabled when the list is populated.

        market_box.AddSpacer(5)
        market_box.Add(self.market_remove, wx.ALIGN_TOP)
        self.dialog_box.Add(market_box)
        # Make a remove button to delete selected market.

        market_add = wx.BoxSizer(orient=wx.HORIZONTAL)

        market_name_label = wx.StaticText(parent=self, label=loc.lan["Market"])

        self.market_name = wx.TextCtrl(parent=self)
        self.market_name.Bind(wx.EVT_TEXT, self.validate_new_market)

        market_middle_label = wx.StaticText(parent=self, label=loc.lan["PricePreposition"])

        self.market_price = wx.TextCtrl(parent=self, style=wx.TE_RIGHT)
        self.market_price.Bind(wx.EVT_TEXT, self.validate_new_market)

        market_price_label = wx.StaticText(parent=self, label="€")

        market_add.Add(market_name_label)
        market_add.AddSpacer(5)
        market_add.Add(self.market_name)
        market_add.AddSpacer(5)
        market_add.Add(market_middle_label)
        market_add.AddSpacer(5)
        market_add.Add(self.market_price)
        market_add.Add(market_price_label)
        self.dialog_box.AddSpacer(5)
        self.dialog_box.Add(market_add)
        # Make a form to add a new market.

        self.add_market = wx.Button(parent=self, label=loc.lan["AddMarket"])
        self.add_market.Bind(wx.EVT_BUTTON, self.on_add_market)
        self.add_market.Disable()  # Disabled by default. Enabled when input is detected as valid.

        self.dialog_box.AddSpacer(5)
        self.dialog_box.Add(self.add_market)
        # Make a button to insert the product into new market.

        button_sizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)  # Add default buttons.
        for item in button_sizer.GetChildren():
            if item.Window and item.Window.GetLabel() == "Cancel":
                item.Window.SetLabel(loc.lan["Cancel"])
                # Convoluted way to translate the Cancel button because wxPython makes it hard to get it.
            if item.Window and item.Window.GetLabel() == "OK":
                self.OK_button = item.Window  # Catch OK button for use with validators.
                self.OK_button.Disable()  # Disabled by default. Enabled by successful validation.

        dialog_sizer = wx.BoxSizer(orient=wx.VERTICAL)
        dialog_sizer.Add(self.dialog_box)
        dialog_sizer.AddSpacer(15)
        dialog_sizer.Add(button_sizer)
        # Add all elements to a sizer to group them together.

        self.SetSizer(dialog_sizer)
        self.Layout()
        self.CentreOnScreen()  # TODO: Make elements properly centred.

    def on_reset_name(self, event):
        """Clears the product name field when the user clicks the restore button."""
        self.product_name.Clear()  # Reset the name field.
        self.reset_name.Disable()  # Disable the restore button (will be re-enabled on change).
        self.name_is_valid = False  # An empty name is not valid.

        event.Skip()

    def on_remove_market(self, event):
        """Remove selected market from the list when the user clicks the appropriate button.

        If there are no more items on the list, the button will be disabled.
        """

        self.market_list.Delete(self.market_list.GetSelection())  # Delete selected market from the list.
        if self.market_list.GetCount() < 1:
            self.market_remove.Disable()  # If there's now fewer than 1 market in the list, disable the remove button.
            self.markets_are_valid = False  # And markets are not valid anymore.
            self.OK_button.Disable()  # So, disable the dialog's OK button.

        event.Skip()

    def on_add_market(self, event):
        """Add a market to the list following the data currently in the form, then empty the form.

        The list will be read when the dialog is accepted and contained markets will be added.
        The remove market button will be re-enabled, in case it was disabled.
        """

        clean_name = self.market_name.Value.strip()
        clean_price = float(re.sub(",", ".", self.market_price.Value.strip()))

        self.market_list.Insert("{market}: {price:0.02f}€".format(market=clean_name,
                                                                  price=clean_price),
                                self.market_list.GetCount())
        # Insert the new market with the entered data.

        self.market_name.Clear()
        self.market_price.Clear()
        # Clear the fields to facilitate a new entry.

        if not self.market_remove.IsEnabled():
            self.market_remove.Enable()
        # Enable the remove market button.

        self.markets_are_valid = True  # Since now there is at least one valid market in the list, markets are valid.
        if self.name_is_valid:
            self.OK_button.Enable()  # Enable the OK button if both name and markets are valid.

        event.Skip()

    def validate_name(self, event):
        """Validate the input when the user enters a product name and en- or disable entering accordingly.

        Invalid fields are signalled by their border becoming red.
        A valid name does not contain only numbers and cannot contain symbols except - and ().
        """

        self.reset_name.Enable()  # In any case, since the input has changed, re-enable the reset button.
        is_valid = False  # By default, input is not valid.
        if re.fullmatch("(?!^[\d ()]+$)^^[^()][ \w()]+$", self.product_name.Value.strip()):
            is_valid = True

        if not is_valid:
            self.product_name.SetBackgroundColour(wx.Colour(red=255, green=150, blue=150, alpha=100))
            self.product_name.Refresh()
            self.name_is_valid = False
            self.OK_button.Disable()
        else:
            self.product_name.SetBackgroundColour(wx.NullColour)
            self.product_name.Refresh()
            self.name_is_valid = True
            if self.markets_are_valid:
                self.OK_button.Enable()  # Only enable the OK button if both name and markets are valid.

        event.Skip()

    def validate_new_market(self, event):
        """Validate the input when the user enters a new market and en- or disable entering accordingly.

        Invalid fields are signalled by their background becoming reddish.
        A valid name cannot contain only numbers and can only contain - as a symbol.
        A valid price only contains numbers and no more than one decimal separator, either . or ,.
        """

        is_name_valid = False  # By default, input is not valid.
        is_price_valid = False  # By default, input is not valid.

        if re.fullmatch("(?!^[\d ()]+$)^^[^()][ \w()]+$", self.market_name.Value.strip()):
            is_name_valid = True

        if re.fullmatch("^\d{1,3}([,.]\d+)?$", self.market_price.Value.strip()):
            is_price_valid = True

        if not is_name_valid:
            self.add_market.Disable()
            self.market_name.SetBackgroundColour(wx.Colour(red=255, green=150, blue=150, alpha=100))
            self.market_name.Refresh()
        else:
            self.market_name.SetBackgroundColour(wx.NullColour)
            self.market_name.Refresh()

        if not is_price_valid:
            self.add_market.Disable()
            self.market_price.SetBackgroundColour(wx.Colour(red=255, green=150, blue=150, alpha=100))
            self.market_price.Refresh()
        else:
            self.market_price.SetBackgroundColour(wx.NullColour)
            self.market_price.Refresh()

        if is_name_valid and is_price_valid:
            self.add_market.Enable()

        event.Skip()


class DeleteDialog(wx.Dialog):
    """Class for a dialog to confirm deletion of an item.

    If the product is present in more than one market, checkboxes are presented to select which markets to delete from.
    """

    def __init__(self, parent, product, in_markets):
        """Create a dialog to ask for confirmation. Format depending on number of markets for the given product."""
        super().__init__(parent=parent,
                         title=loc.lan["ConfirmDeletionDialog"],
                         style=wx.DEFAULT_DIALOG_STYLE)

        dialog_box = wx.BoxSizer(orient=wx.VERTICAL)  # Make a box to hold the dialog elements.

        instructions_text = "{text}: {product}?".format(text=loc.lan["ConfirmDeletionOne"], product=product)
        # Write instructions for the user depending on language.

        if len(in_markets) == 1:  # If there's only one market to delete the item from.
            instructions_label = wx.StaticText(parent=self,
                                               label=instructions_text)
            dialog_box.Add(instructions_label, size_option_CTR)
            # Only add basic instructions.
        else:  # If there's more than one market.
            instructions_text += "\n{text}:".format(text=loc.lan["ConfirmDeletionTwo"])
            instructions_label = wx.StaticText(parent=self,
                                               label=instructions_text)
            dialog_box.Add(instructions_label, size_option_CTR)
            # Instruct the user to select the markets to delete from.
            for market in in_markets:
                checkbox = wx.CheckBox(parent=self, label=market[0], name=market[0])
                dialog_box.Add(checkbox)
                # Add a checkbox for each market and label it.

        button_sizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)  # Add default buttons.
        for item in button_sizer.GetChildren():
            if item.Window and item.Window.GetLabel() == "Cancel":
                item.Window.SetLabel(loc.lan["Cancel"])
        # Convoluted way to translate the Cancel button because wxPython makes it hard to get it.

        dialog_sizer = wx.BoxSizer(orient=wx.VERTICAL)
        dialog_sizer.Add(dialog_box, size_option_CTR)
        dialog_sizer.Add(button_sizer, size_option_CTR)
        # Add all elements to a sizer to group them together.

        self.SetSizer(dialog_sizer)
        self.Layout()
        self.CentreOnScreen()  # TODO: Make elements properly centred.


class MainWindow(wx.Frame):
    """Class for the main window."""
    def __init__(self):
        """Initialise the main window."""
        super().__init__(parent=None, id=-1,
                         title="MarktComparator",
                         style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX), size=wx.Size(800, 600))

        # Make a panel to provide tab functionality to the main window.
        self.main_panel = wx.Panel(parent=self, size=wx.Size(800, 600))

        # Make a label to display the output and a button to copy its contents to clipboard.
        self.output_label = OutputLabel(parent=self.main_panel)

        output_clipboard_button = wx.Button(parent=self.main_panel, label=loc.lan["Clipboard"])
        output_clipboard_button.Bind(wx.EVT_BUTTON,             self.on_clipboard_button)

        # START of io_grid elements
        # Make a list for products and a search box.
        self.search_input = wx.SearchCtrl(parent=self.main_panel,
                                          style=wx.TE_PROCESS_ENTER)
        self.search_input.SetDescriptiveText(loc.lan["SearchBox"])  # TODO: Add keyboard shortcuts and mnemonics.

        self.search_input.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN,    self.on_search)
        self.search_input.Bind(wx.EVT_TEXT,                     self.on_search)
        self.search_input.Bind(wx.EVT_TEXT_ENTER,               self.on_search)

        self.product_list = ProductList(parent=self.main_panel)
        self.product_list.Bind(wx.EVT_LISTBOX,                  self.on_product_selection)
        # END of io_grid elements

        # START of button_grid
        # Make the buttons for input from user.
        # # One to edit selected item.
        # # One to delete selected item.
        # # One to add a new item.
        # TODO: Add keyboard shortcuts to all buttons and mnemonics to all languages.
        edit_button = wx.Button(parent=self.main_panel, label=loc.lan["EditItem"] + "...")
        edit_button.Bind(wx.EVT_BUTTON,                         self.on_edit_button)

        delete_button = wx.Button(parent=self.main_panel, label=loc.lan["DeleteItem"] + "...")
        delete_button.Bind(wx.EVT_BUTTON,                       self.on_delete_button)

        add_button = wx.Button(parent=self.main_panel, label=loc.lan["NewItem"] + "...")
        add_button.Bind(wx.EVT_BUTTON,                          self.on_new_button)
        # END of button_grid

        # Make a status bar to show the outcome/errors and a drop-down for language selection.
        status_bar = wx.StatusBar(parent=self,
                                  style=(wx.STB_SHOW_TIPS |
                                         wx.STB_ELLIPSIZE_END |
                                         wx.FULL_REPAINT_ON_RESIZE))
        self.SetStatusBar(status_bar)

        language_selection = LanguageSelector(parent=status_bar)

        # Get each status bar element's width and set the panes' widths accordingly.
        language_selection_width = language_selection.Size[0]
        status_bar_width = status_bar.Size[0]
        status_bar_width -= language_selection_width
        status_bar.SetStatusWidths([status_bar_width])
        language_selection.SetPosition((status_bar_width + 2, 0))

        self.SetStatusText(loc.lan["StatusBar"])  # Set status message to the default (greeting the user)

        # Set all elements in grids.
        # Make a grid to display search_input and product_list on top of each other.
        product_compound = wx.GridSizer(cols=1)
        product_compound.Add(self.search_input, size_option_CTR)
        product_compound.Add(self.product_list, size_option_FIT)
        # Make a grid to display output_label and output_clip on top of each other.
        output_compound = wx.GridSizer(cols=1)
        output_compound.Add(self.output_label, size_option_FIT)
        output_compound.Add(output_clipboard_button, size_option_FIT)
        # Make a grid to group the above grids into a single row.
        io_grid = wx.GridSizer(cols=2)
        io_grid.Add(product_compound, size_option_FIT)
        io_grid.Add(output_compound, size_option_FIT)

        # Make a grid to display the buttons side by side.
        button_grid = wx.GridSizer(cols=3)
        button_grid.Add(edit_button, size_option_CTR)
        button_grid.Add(add_button, size_option_CTR)
        button_grid.Add(delete_button, size_option_CTR)

        # Make a main grid to contain the above grids.
        main_grid = wx.GridSizer(cols=1)
        main_grid.Add(io_grid, size_option_FIT)
        main_grid.Add(button_grid, size_option_FIT)

        # Finalise layout and draw it.
        # TODO: Resize and reposition all elements properly.
        self.SetSizer(main_grid)  # Designate main_grid as the layout of the window
        self.Layout()  # Auto-size the layout
        self.CentreOnScreen()
        self.Show(True)

    def on_clipboard_button(self, event):
        """Copy the current output to user's clipboard when they click the appropriate button.

        Do not modify the clipboard if the output is the default one.
        """

        if wx.TheClipboard.Open() and self.output_label.GetLabel() != loc.lan["DefaultOutput"]:
            # Ensure the clipboard is accessible and the output is not the default one.
            to_clip = wx.TextDataObject(self.output_label.GetLabel())  # Prepare the string from the output.
            wx.TheClipboard.SetData(to_clip)  # Replace the clipboard with the output.
            wx.TheClipboard.Flush()  # Flush to make sure the clipboard is not emptied on product exit.
            wx.TheClipboard.Close()  # De-access the clipboard.
        event.Skip()

    def on_product_selection(self, event):
        """Pass the event to the output formatter when the user selects a product."""
        self.output_label.SetLabel(self.product_list.on_selection_change())
        try:
            event.Skip()
        except AttributeError:  # Dirty way to handle when I call this without a proper event.
            return

    def on_search(self, event):
        """Find the closest-matching product name when the user searches by using the search input."""
        search_text = self.search_input.GetValue()
        if search_text.strip():
            found_product = self.product_list.FindString(search_text)
            # TODO: Rework with fuzzystr match: https://docs.python.org/3/library/difflib.html#difflib.get_close_matches
            if found_product is not wx.NOT_FOUND:
                self.product_list.SetSelection(found_product)
                self.on_product_selection(wx.EVT_LISTBOX)
        event.Skip()

    def on_edit_button(self, event):
        """Prompt a dialog asking for information when the user presses the 'edit product' button."""
        try:  # to find the element in the product list.
            product = self.product_list.GetString(self.product_list.GetSelection())
        except AssertionError:
            self.SetStatusText(loc.lan["StatusBarNoSelection"])  # If nothing is selected, insult the user and return.
            return

        in_markets = find_product(product)  # Get list of market/prices for selected product.
        if len(in_markets) == 0:
            self.SetStatusText(loc.lan["StatusBarNoSelection"])
        else:
            dialog = EditDialog(parent=self, in_markets=in_markets, product=product)
            dialog_result = dialog.ShowModal()  # Show a dialog to prompt for input.

            if dialog_result == wx.ID_OK:  # If user didn't cancel.
                delete_product(product)  # Delete the product from everywhere.
                new_name = dialog.product_name.Value  # Store new product name (which could be the same as before).

                for entry in dialog.market_list.GetItems():
                    current_market_name, current_market_price = entry.split(": ")
                    clean_price = float(current_market_price.rstrip("€"))
                    update_product(new_name, current_market_name, clean_price)
                # Add (new) product name to all markets present in the input.

                self.product_list.repopulate()  # Rebuild the product list in the GUI.
                self.SetStatusText(loc.lan["EditSuccess"])
            else:
                self.SetStatusText(loc.lan["StatusBarCancel"])
        event.Skip()

    def on_new_button(self, event):
        """Prompt a dialog asking for information when the user presses the 'new item' button."""
        dialog = NewDialog(parent=self)
        dialog_result = dialog.ShowModal()

        if dialog_result == wx.ID_OK:  # If user didn't cancel.
            if not find_product(dialog.product_name.Value):
                for entry in dialog.market_list.GetItems():
                    current_market_name, current_market_price = entry.split(": ")
                    clean_price = float(current_market_price.rstrip("€"))
                    update_product(dialog.product_name.Value, current_market_name, clean_price)
                    # Add new product to database.

                    self.product_list.repopulate()  # Rebuild the product list in the GUI.
                    self.SetStatusText(loc.lan["NewSuccess"])
            else:
                self.SetStatusText(loc.lan["NewFailure"])
        else:
            self.SetStatusText(loc.lan["StatusBarCancel"])

        event.Skip()

    def on_delete_button(self, event):
        """Prompt a dialog asking for confirmation when the user presses the 'delete product' button."""
        product = self.product_list.GetString(self.product_list.GetSelection())
        in_markets = find_product(product)
        if len(in_markets) == 0:
            self.SetStatusText(loc.lan["StatusBarNoSelection"])
        else:
            confirmation = DeleteDialog(parent=self, in_markets=in_markets, product=product)
            confirmation_result = confirmation.ShowModal()

            if confirmation_result == wx.ID_OK:
                if len(in_markets) > 1:
                    delete_from_markets = [window.Name
                                           for window in confirmation.GetChildren()
                                           if isinstance(window, wx.CheckBox)
                                           and window.GetValue() is True]
                    if len(delete_from_markets) == 0:
                        self.SetStatusText(loc.lan["StatusBarCancel"])
                    else:
                        if delete_product(product, delete_from_markets):
                            self.product_list.repopulate()
                            if self.product_list.FindString(product) != wx.NOT_FOUND:
                                self.on_product_selection(wx.EVT_LISTBOX)
                            self.SetStatusText(loc.lan["DeleteSuccess"])
                        else:
                            self.SetStatusText(loc.lan["DeleteFailure"])
                else:
                    if delete_product(product, in_markets[0][0]):
                        self.product_list.repopulate()
                        self.SetStatusText(loc.lan["DeleteSuccess"])
                    else:
                        self.SetStatusText(loc.lan["DeleteFailure"])
            else:
                self.SetStatusText(loc.lan["StatusBarCancel"])

        event.Skip()


if __name__ == "__main__":
    app = wx.App(False)
    main_window = MainWindow()
    app.SetTopWindow(main_window)
    app.MainLoop()
