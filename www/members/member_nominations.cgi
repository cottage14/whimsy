#!/usr/bin/env ruby
PAGETITLE = "Add entries to member nomination file" # Wvisible:tools
# Note: PAGETITLE must be double quoted

$LOAD_PATH.unshift '/srv/whimsy/lib'
require 'wunderbar'
require 'wunderbar/bootstrap'
require 'whimsy/asf'
require 'whimsy/asf/forms'
require 'whimsy/asf/member-files'

def emit_form(title, prev_data)
  _whimsy_panel(title, style: 'panel-success') do
    _form.form_horizontal method: 'post' do
      _whimsy_forms_subhead(label: 'Nomination Form')
      field = 'availid'
      _whimsy_forms_input(label: 'Nominee availid', name: field,
        value: prev_data[field], helptext: 'Enter the availid of the potential member'
      )
      _whimsy_forms_input(label: 'Nominated by', name: 'nomby', readonly: true, value: $USER
      )
      field = 'statement'
      _whimsy_forms_input(label: 'Nomination statement', name: field, rows: 10,
        value: prev_data[field], helptext: 'Reason for nomination'
      )
      _whimsy_forms_submit
    end
  end
end

# Validation as needed within the script
# Returns: 'OK' or a text message describing the problem
def validate_form(formdata: {})
  uid = formdata['availid']
  chk = ASF::Person[uid]&.asf_member?
  chk.nil? and return "Invalid availid: #{uid}"
  chk and return "Already a member: #{uid}"
  already = ASF::MemberFiles.member_nominees
  return "Already nominated: #{uid} by #{already[uid]['Nominated by']}" if already.include? uid
  return 'OK'
end

# Hack to ensure multiple lines are in the same 'pre' block
module Wunderbar
  class XmlMarkup
    def system(*args)
      opts = {}
      opts = args.pop if Hash === args.last

      tag = opts[:tag] || 'pre'
      merge_lines = tag == 'pre' # merge lines of the same type
      output_class = opts[:class] || {}
      output_class[:stdin]  ||= '_stdin'
      output_class[:stdout] ||= '_stdout'
      output_class[:stderr] ||= '_stderr'
      output_class[:hilite] ||= '_stdout _hilite'

      out = []
      okind = nil
      rc = super(*args, opts) do |kind, line|
        if merge_lines
          if okind && kind != okind && !out.empty? # change of kind
            tag! tag, out.join("\n"), class: output_class[okind]
            out = []
          end
          out << line
        else # normal; no accumulation of lines
          tag! tag, line, class: output_class[kind]
        end
        okind = kind
      end
      # Output last line(s)
      unless out.empty?
        tag! tag, out.join("\n"), class: output_class[okind]
      end
      return rc
    end
  end
end

# Handle submission (checkout user's apacheid.json, write form data, checkin file)
# @return true if we think it succeeded; false in all other cases
def process_form(formdata: {}, wunderbar: {})
  statement = formdata['statement']

  _h3 'Copy of statement to put in an email (if necessary)'
  _pre statement

  _hr

  _h3 'Transcript of update to nomination file'
  uid = formdata['availid']
  entry = ASF::MemberFiles.make_member_nomination({
    availid: uid,
    nomby: $USER,
    statement: statement
  })

  environ = Struct.new(:user, :password).new($USER, $PASSWORD)
  ASF::MemberFiles.update_member_nominees(environ, wunderbar, [entry], "+= #{uid}")
  return true
end

# Produce HTML
_html do
  _body? do # The ? traps errors inside this block
    _whimsy_body( # This emits the entire page shell: header, navbar, basic styles, footer
      title: PAGETITLE,
      subtitle: 'About This Script',
      relatedtitle: 'More Useful Links',
      related: {
        "/committers/tools" => "Whimsy Tool Listing",
        "https://incubator.apache.org/images/incubator_feather_egg_logo_sm.png" => "Incubator Logo, to show that graphics can appear",
        "https://community.apache.org/" => "Get Community Help",
        "https://github.com/apache/whimsy/blob/master/www#{ENV['SCRIPT_NAME']}" => "See This Source Code"
      },
      helpblock: -> {
        _h3 'BETA - please report any errors to the Whimsy PMC!'
        _p %{
          This form can be used to ADD entries to the nominated-members.txt file.
          This is currently for use by the Nominator only, and does not send a copy
          of the nomination to the members list.
          There is currently no support for updating an existing entry.
        }
      }
    ) do

      _div id: 'nomination-form' do
        if _.post?
          submission = _whimsy_params2formdata(params)
          valid = validate_form(formdata: submission)
          if valid == 'OK'
            if process_form(formdata: submission, wunderbar: _)
              _p.lead "Thanks for Using This Form!"
            else
              _div.alert.alert_warning role: 'alert' do
                _p "SORRY! Your submitted form data failed process_form, please try again."
              end
            end
          else
            _div.alert.alert_danger role: 'alert' do
              _p "SORRY! Your submitted form data failed validate_form, please try again."
              _p valid
            end
          end
        else # if _.post?
          emit_form('Enter nomination data', {})
        end
      end
    end
  end
end
