import functools
from webdriver_components.pageobjects import Component, ComponentMetaclass, Css


class TableRowMetaclass(ComponentMetaclass):
    """
        class PayRateRow(TableRow):
            cell_names = (
                'from_date', 
                'pay_rate', 
                'charge_out_rate'
            )

    is roughly a shortcut for:

        class PayRateRow(MyPageObject):
            from_date_cell = Css("td:nth-child(1)")
            pay_rate_cell = Css("td:nth-child(2)")
            charge_out_rate_cell = Css("td:nth-child(3)")

            @property
            def from_date(self):
                return self.from_date_cell.text.strip()

            @property
            def pay_rate(self):
                return self.pay_rate_cell.text.strip()

            @property
            def charge_out_rate(self):
                return self.charge_out_rate_cell.text.strip()

            @property
            def data(self):
                return {
                    'from_date': self.from_date,
                    'pay_rate': self.pay_rate,
                    'charge_out_rate': self.charge_out_rate,
                }
    """

    def __new__(mcl, name, bases, attrs):
        cell_names = attrs.pop('cell_names', [])

        def cell_prop_name(cell_name):
            return cell_name + '_cell'

        attrs = {
            **attrs,
            **({
                cell_prop_name(name): Css("td:nth-child({})".format(i + 1))
                for i, name in enumerate(cell_names)
            })
        }

        def getter(self, cell_prop_name):
            return getattr(self, cell_prop_name).text.strip()

        for c in cell_names:
            attrs[c] = property(functools.partial(getter, cell_prop_name=cell_prop_name(c)))

        @property
        def data(self):
            return {c: getattr(self, c) for c in cell_names}
        attrs['data'] = data

        return super(TableRowMetaclass, mcl).__new__(mcl, name, bases, attrs)


class TableRow(Component, metaclass=TableRowMetaclass):
    pass


