#!/usr/bin/env python3

# For the latest information about this program, see https://github.com/willemw12/xmltv2rss

import argparse
import io
import os.path
import sys
import xml.etree.ElementTree as ElementTree

from datetime import datetime, timezone

# RFC-2822 formatted datetime
from email import utils
# from xml.dom.minidom import parseString
# from xml.etree.ElementTree import ElementTree

DEFAULT_XMLTV_DATETIME_FORMAT = "%Y%m%d%H%M%S %z"
DEFAULT_XMLTV_DATETIME_FORMAT_UTC = "%Y%m%d%H%M%S"

DEFAULT_RSS_CHANNEL_DESCRIPTION = "Generated by xmltv2rss"
DEFAULT_RSS_CHANNEL_LANGUAGE = "en"
DEFAULT_RSS_CHANNEL_LINK = ""
DEFAULT_RSS_CHANNEL_TITLE = "XMLTV feed"


def _convert(args):
    RSS_CHANNEL_TEMPLATE = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>%(title)s</title>
    <link>%(link)s</link>
    <description>%(description)s</description>
    <lastBuildDate>%(created_on)s</lastBuildDate>
    <pubDate>%(pub_date)s</pubDate>
    <language>%(language)s</language>
  </channel>
</rss>
"""

    RSS_ITEM_TEMPLATE = """
    <item>
      <title><![CDATA[%(title)s]]></title>
      <link></link>
      <description><![CDATA[%(description)s]]></description>
      <guid>%(guid)s</guid>
      <pubDate>%(pub_date)s</pubDate>
    </item>
"""

    # Pretty print
    RSS_ITEM_HEAD_TEMPLATE = """
    """

    # Pretty print
    RSS_ITEM_TAIL_TEMPLATE = """
  """

    RSS_ITEM_DESCRIPTION_TEMPLATE = """
         <table>
            <tr><td align="right" valign="top">Title:</td><td>%(title)s</td></tr>
            <tr><td align="right" valign="top">Channel:</td><td>%(channel)s</td></tr>
            <tr><td align="right" valign="top">Airdate:</td><td>%(airdate)s</td></tr>
            <tr><td align="right" valign="top">Airtime:</td><td>%(airtime)s</td></tr>
            <tr><td align="right" valign="top" style="white-space: nowrap">Length:</td><td>%(airtime_length)s</td></tr>
            <tr><td align="right" valign="top">Category:</td><td>%(category)s</td></tr>
            <tr><td align="right" valign="top">Description:</td><td>%(desc)s</td></tr>
         </table>
      """

    #    RSS_CHANNEL_TEMPLATE = \
    #        '<?xml version="1.0" encoding="UTF-8" ?>' + \
    #        '<rss version="2.0">' + \
    #          '<channel>' + \
    #            '<title>%(title)s</title>' + \
    #            '<link>%(link)s</link>' + \
    #            '<description>%(description)s</description>' + \
    #            '<lastBuildDate>%(created_on)s</lastBuildDate>' + \
    #            '<pubDate>%(pub_date)s</pubDate>' + \
    #            '<language>%(language)s</language>' + \
    #          '</channel>' + \
    #        '</rss>'
    #
    #    RSS_ITEM_TEMPLATE = \
    #        '<item>' + \
    #          '<title><![CDATA[%(title)s]]></title>' + \
    #          '<link></link>' + \
    #          '<description><![CDATA[%(description)s]]></description>' + \
    #          '<guid>%(guid)s</guid>' + \
    #          '<pubDate>%(pub_date)s</pubDate>' + \
    #        '</item>'

    # try:

    # from xml.etree.ElementTree import ElementTree
    # xmltv_tree = ElementTree()
    # xmltv_tree.parse(args.input_filename)
    xmltv_tree = ElementTree.parse(args.input_filename)

    # except xml.etree.ElementTree.ParseError as exc:
    #    ...

    if isinstance(args.input_filename, str):
        # Get modification time from the input file
        timestamp = os.path.getmtime(args.input_filename)
        pub_date = utils.formatdate(timestamp, localtime=True)
    else:
        pub_date = utils.formatdate(localtime=True)
    created_on = utils.formatdate(localtime=True)

    rss_channel_dict = dict(
        title=args.feed_title,
        link=args.feed_url,
        description=args.feed_description,
        pub_date=pub_date,
        created_on=created_on,
        language=args.feed_language,
    )
    rss_channel_str = RSS_CHANNEL_TEMPLATE % rss_channel_dict

    rss_tree = ElementTree.ElementTree()
    # rss_tree.parse('rss_channel_template.xml')
    rss_tree.parse(io.StringIO(rss_channel_str))

    rss_channel = rss_tree.find("channel")
    if rss_channel is not None:
        # Pretty print
        #
        # TODO: Return the last child, not the first child
        # last_child = channel.find('*[last()]')
        #
        # last_child = channel.find('language')
        children = rss_channel.findall("*")
        last_child = children[len(children) - 1]
        last_child.tail = RSS_ITEM_HEAD_TEMPLATE

        # programs = iterfind('programme')
        programs = xmltv_tree.findall("programme")
        if programs is not None:
            for i, program in enumerate(programs):
                channel_id = program.get("channel", default="")
                title = program.findtext("title", default="")
                desc = program.findtext("desc", default="")
                category = program.findtext("category", default="")

                starttime = program.get("start", default="")
                stoptime = program.get("stop", default=starttime)

                channel_callsign = xmltv_tree.findtext(
                    "./channel[@id='" + channel_id + "']/display-name"
                )
                channel = "{}-{}".format(channel_id, channel_callsign)

                # starttime/stoptime are format "YYYYMMDDHHMMSS ±HHMM" or just "YYYYMMDDHHMMSS"
                # (assuming UTC), so we retry if parsing with timezone fails
                try:
                    starttime_dt = datetime.strptime(
                        starttime, args.xmltv_datetime_format
                    )
                except ValueError:
                    starttime_dt = datetime.strptime(
                        starttime, DEFAULT_XMLTV_DATETIME_FORMAT_UTC
                    ).replace(tzinfo=timezone.utc)

                try:
                    stoptime_dt = datetime.strptime(
                        stoptime, args.xmltv_datetime_format
                    )
                except ValueError:
                    stoptime_dt = datetime.strptime(
                        stoptime, DEFAULT_XMLTV_DATETIME_FORMAT_UTC
                    ).replace(tzinfo=timezone.utc)

                # Adjust start and stop time to local timezone.
                # This also fixes airdate/airtime to display in local (not original) timezone.
                # No need to import tzlocal when using .astimezone().
                starttime_dt = starttime_dt.astimezone()
                stoptime_dt = stoptime_dt.astimezone()

                # No need to determine the timezone.
                # The starttime and stoptime strings already contain the timezone
                airdate = datetime.strftime(starttime_dt, args.feed_date_format[0])
                airtime = (
                    datetime.strftime(starttime_dt, args.feed_time_format[0])
                    + " - "
                    + datetime.strftime(stoptime_dt, args.feed_time_format[0])
                )

                # Airtime length in hours and minutes
                airtime_length_td = stoptime_dt - starttime_dt
                airtime_length_mins = airtime_length_td.seconds // 60
                airtime_length = (
                    "{0:2}".format(airtime_length_mins // 60)
                    + ":"
                    + "{0:02}".format(airtime_length_mins % 60)
                    + ":00"
                )

                # EPG <desc> allows newlines. Make them <br/> for prettier display
                desc = "<br/>".join(desc.splitlines())

                guid = channel_id + "-" + starttime_dt.strftime("%Y%m%d%H%M%S")
                pub_date = utils.formatdate(starttime_dt.timestamp(), localtime=True)

                description_dict = dict(
                    title=title,
                    channel=channel,
                    airdate=airdate,
                    airtime=airtime,
                    airtime_length=airtime_length,
                    desc=desc,
                    category=category,
                )
                description_str = RSS_ITEM_DESCRIPTION_TEMPLATE % description_dict

                item_dict = dict(
                    title=title,
                    # sub_title=sub_title,
                    # link=link,
                    description=description_str,
                    guid=guid,
                    pub_date=pub_date,
                )
                item_str = RSS_ITEM_TEMPLATE % item_dict
                item = ElementTree.fromstring(item_str)

                # Pretty print
                if i < len(programs) - 1:
                    item.tail = RSS_ITEM_HEAD_TEMPLATE
                else:
                    item.tail = RSS_ITEM_TAIL_TEMPLATE

                rss_channel.append(item)

    rss_tree.write(sys.stdout, encoding="unicode")

    # rss_tree_str = xml.etree.ElementTree.tostring(rss_tree.getroot(), encoding='unicode')
    # print(parseString(rss_tree_str).toprettyxml(indent='  ', newl='\n'))


def _main():
    parser = argparse.ArgumentParser(
        description="Generate an RSS feed from an XMLTV (tvguide) listing. Print the result to standard output.",
        epilog='For information about date and time format strings ("%Y", "%H", etc.), search for "datetime" on https://docs.python.org.',
    )
    parser.add_argument(
        "--feed-date-format",
        "-d",
        nargs=1,
        default=["%a %d %B, %Y"],
        help='examples: "%%Y-%%m-%%d", "%%a %%d %%B, %%Y", "%%x"',
    )
    parser.add_argument(
        "--feed-language",
        default=DEFAULT_RSS_CHANNEL_LANGUAGE,
        help='RSS feed language. Default: "' + DEFAULT_RSS_CHANNEL_LANGUAGE + '"',
    )
    parser.add_argument(
        "--feed-time-format",
        "-t",
        nargs=1,
        default=["%H:%M"],
        help='examples: "%%H:%%M", "%%I:%%M %%p", "%%X"',
    )
    parser.add_argument(
        "--feed-title", default=DEFAULT_RSS_CHANNEL_TITLE, help="RSS feed title"
    )
    parser.add_argument(
        "--feed-url",
        default=DEFAULT_RSS_CHANNEL_LINK,
        # help='RSS feed link. Default: "' + DEFAULT_RSS_CHANNEL_LINK + '"')
        help="RSS feed link",
    )
    # parser.add_argument(
    #    "--indent",
    #    action="store_const",
    #    const=True,
    #    default=2,
    #    help="Output XML indentation",
    # )
    parser.add_argument(
        "--xmltv-datetime-format",
        nargs=1,
        default=DEFAULT_XMLTV_DATETIME_FORMAT,
        help='XMLTV date and time format. Default: "'
        + DEFAULT_XMLTV_DATETIME_FORMAT.replace("%", "%%")
        + '", default fallback: "'
        + DEFAULT_XMLTV_DATETIME_FORMAT_UTC.replace("%", "%%")
        + '"',
    )
    parser.add_argument(
        "input_filename",
        metavar="<file>",
        nargs="?",
        default=sys.stdin,
        help="XMLTV input file",
    )
    parser.set_defaults(feed_description=DEFAULT_RSS_CHANNEL_DESCRIPTION)
    args = parser.parse_args()
    # indent = args.indent

    _convert(args)


if __name__ == "__main__":
    _main()
