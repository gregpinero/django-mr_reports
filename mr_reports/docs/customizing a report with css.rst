Customizing a Report with CSS
===== 

To customize the style of a report, create a new Style record in the Styles table, and
reference it from your report using the "style" field.

A style record should contain ordinary CSS that manipulates for styles the existing HTML 
on the report page.


Examples
------

Change the background color of the report header and put in a logo::

    div.jumbotron {
        background-color: #EBF8FE;
        background-image: url('/static/images/gray_janelia_logo.png');
        background-repeat: no-repeat;
        background-position: top right;
    }


