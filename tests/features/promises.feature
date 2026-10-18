Feature: Delfona user promises
  Scenario Outline: Language survives page navigation
    Given a visitor on the live page
    When the visitor selects "<language>" and opens My assets
    Then the selected language is "<language>"
    Examples:
      | language |
      | ko       |
      | en       |

  Scenario: Saved assets lead the live market strip
    Given a visitor on the live page
    Then the first market assets are BTC ETH NVDA

  Scenario: Three daily insights replace the review
    Given a visitor on the daily page
    Then three insights are visible and the review is absent

  Scenario: Theme pages explain today's stories
    Given a visitor on the theme page
    Then a theme summary box is visible

  Scenario: Upcoming calendar releases have one box
    Given a visitor on the calendar page
    Then upcoming releases are in one box

  Scenario: Story details close with the close button
    Given a visitor on the live page
    When the visitor opens a story and presses close
    Then the story dialog is hidden and marked hidden

  Scenario: Story details close with Escape
    Given a visitor on the live page
    When the visitor opens a story and presses Escape
    Then the story dialog is hidden and marked hidden

  Scenario: Calendar history supports the keyboard
    Given a visitor on the calendar page
    When the visitor moves through the history chart with arrow keys
    Then the chart's accessible readout changes

  Scenario: Public stories do not expose Telegram sources
    Given a visitor on the live page
    Then no Telegram source or link is visible

  Scenario: Saved assets appear in My assets
    Given a visitor on the my page
    Then the saved watchlist has BTC ETH NVDA

  Scenario: Bullish filter selects bullish stories
    Given a visitor on the live page
    When the visitor selects the bullish filter
    Then every grid story is bullish

  Scenario: An economic indicator opens its history
    Given a visitor on the calendar page
    When the visitor selects a different indicator
    Then the selected indicator has a detail panel

  Scenario: A thread opens its story history
    Given a visitor on the brief page
    When the visitor selects a thread
    Then the thread details are visible
