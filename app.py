<div class="layout" style="padding: 15px; height: 100%;">
  
  <!-- ROW 1: HEADER & RESORT OVERVIEW -->
  <div class="columns border--bottom padding-bottom--1">
    <div class="column" style="width: 60%;">
      <span class="title font--xlarge" data-pixel-perfect="true">GEMSSTOCK</span>
      <span class="description font--medium" style="margin-top: 2px;">Andermatt High Alpine Peak</span>
    </div>
    <div class="column text--right" style="width: 40%;">
      <span class="value font--xlarge">{{ summary.open }}/{{ summary.total }}</span>
      <span class="label">Lifts Running</span>
    </div>
  </div>

  <!-- ROW 2: CONDITIONS DASHBOARD METRICS -->
  <div class="columns padding-vertical--2 border--bottom bg--grey-light" style="margin-top: 10px; border-radius: 4px;">
    <div class="column text--center" style="width: 33%;">
      <span class="label block">Air Temp</span>
      <span class="value font--large">{{ weather.temp }}°C</span>
      <span class="description font--small">{{ weather.condition }}</span>
    </div>
    <div class="column text--center style="width: 33%; border-left: 1px solid #000; border-right: 1px solid #000;">
      <span class="label block">Fresh Snow</span>
      <span class="value font--large">+{{ weather.new_snow_cm }} cm</span>
      <span class="description font--small">Past 24 Hours</span>
    </div>
    <div class="column text--center" style="width: 33%;">
      <span class="label block">Base Depth</span>
      <span class="value font--large">{{ weather.snow_depth_cm }} cm</span>
      <span class="description font--small">Summit Station</span>
    </div>
  </div>

  <!-- ROW 3: EXPLODED LIFT LIST MATRIX -->
  <div class="padding-top--2" style="margin-top: 5px;">
    <span class="label font--medium block padding-bottom--1" style="text-transform: uppercase; letter-spacing: 1px;">Installation Status</span>
    
    <div class="columns flex-wrap">
      {% for lift in lifts %}
      <div class="column" style="width: 50%; padding-bottom: 8px;">
        <div class="item style="padding-right: 15px;">
          <div class="meta">
            <!-- Keeps typography perfectly balanced -->
            <span class="title font--small" style="font-weight: bold;">{{ lift.name }}</span>
          </div>
          <div class="content text--right">
            {% if lift.status == 'Open' %}
              <span class="tag tag--black">OPEN</span>
            {% else %}
              <span class="tag tag--light" style="border: 1px solid #000;">CLOSED</span>
            {% endif %}
          </div>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>

  <!-- TIMESTAMPS FOOTER -->
  <div class="title_bar" style="position: absolute; bottom: 10px; width: 95%;">
    <span class="title_bar__text">TRMNL X Alpine Feed • Sync: {{ "now" | date: "%H:%M" }}</span>
  </div>
</div>