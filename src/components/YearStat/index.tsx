import React from 'react';
import Stat from '@/components/Stat';
import WorkoutStat from '@/components/WorkoutStat';
import useActivities from '@/hooks/useActivities';
import {
  AVG_HEART_RATE_LABEL,
  FAILED_TO_LOAD_SVG_LABEL,
  IS_CHINESE,
  JOURNEY_LABEL,
  LOADING_LABEL,
  STREAK_LABEL,
  TOTAL_LABEL,
} from '@/utils/const';
import { colorFromType, titleForType } from '@/utils/utils';
import styles from './style.module.scss';
import useHover from '@/hooks/useHover';
import { yearStats } from '@assets/index'

const YearStat = ({ year, onClick }: { year: string, onClick: (_year: string) => void }) => {
  let { activities: runs, years } = useActivities();
  // for hover
  const [hovered, eventHandlers] = useHover();
  // lazy Component
  const YearSVG = React.lazy(() => yearStats[`./year_${year}.svg`]()
    .then((res) => ({ default: res }))
    .catch((err) => {
      console.error(err);
      return { default: () => <div>{FAILED_TO_LOAD_SVG_LABEL}</div> };
    })
  );

  if (years.includes(year)) {
    runs = runs.filter((run) => run.start_date_local.slice(0, 4) === year);
  }
  let sumDistance = 0;
  let streak = 0;
  let heartRate = 0;
  let heartRateNullCount = 0;
  const workoutsCounts: Record<string, [number, number, number]> = {
    Ride: [0, 0, 0],
    VirtualRide: [0, 0, 0],
    'Indoor Ride': [0, 0, 0],
  };

  runs.forEach((run) => {
    sumDistance += run.distance || 0;
    if (run.average_speed) {
      if (workoutsCounts[run.type]) {
        const [oriCount, oriSecondsAvail, oriMetersAvail] = workoutsCounts[run.type];
        workoutsCounts[run.type] = [
          oriCount + 1,
          oriSecondsAvail + (run.distance || 0) / run.average_speed,
          oriMetersAvail + (run.distance || 0),
        ];
      } else {
        workoutsCounts[run.type] = [1, (run.distance || 0) / run.average_speed, run.distance];
      }
    }
    if (run.average_heartrate) {
      heartRate += run.average_heartrate;
    } else {
      heartRateNullCount++;
    }
    if (run.streak) {
      streak = Math.max(streak, run.streak);
    }
  });
  const hasHeartRate = !(heartRate === 0);
  const avgHeartRate = (heartRate / (runs.length - heartRateNullCount)).toFixed(
    0
  );

  const bikeTypes = ['Ride', 'VirtualRide', 'Indoor Ride'];
  const bikeTypeSet = new Set(bikeTypes);
  const bikeWorkouts = bikeTypes
    .filter((type) => workoutsCounts[type] !== undefined)
    .map((type) => [type, workoutsCounts[type]] as [string, [number, number, number]]);

  const otherWorkouts = Object.entries(workoutsCounts)
    .filter(([type, count]) => !bikeTypeSet.has(type) && count[0] > 0)
    .sort((a, b) => b[1][0] - a[1][0]);

  const workoutsArr = [...bikeWorkouts, ...otherWorkouts];
  return (
    <div
      style={{ cursor: 'pointer' }}
      onClick={() => onClick(year)}
      {...eventHandlers}
    >
      <section>
        <Stat value={year === 'Total' ? TOTAL_LABEL : year} description={JOURNEY_LABEL} />
        { sumDistance > 0 &&
          <WorkoutStat
            key='total'
            value={runs.length}
            description={` ${TOTAL_LABEL}`}
            distance={(sumDistance / 1000.0).toFixed(0)}
          />
        }
        { workoutsArr.map(([type, count]) => (
          <WorkoutStat
            key={type}
            value={count[0]}
            description={` ${titleForType(type)}${IS_CHINESE ? '' : count[0] > 1 ? 's' : ''}`}
            distance={(count[2] / 1000.0).toFixed(0)}
            color={colorFromType(type)}
          />
        ))}
        <Stat
          value={IS_CHINESE ? streak : `${streak} day`}
          description={STREAK_LABEL}
          className="mb0 pb0"
        />
        {hasHeartRate && (
          <Stat value={avgHeartRate} description={AVG_HEART_RATE_LABEL} />
        )}
      </section>
      {year !== "Total" && hovered && (
        <React.Suspense fallback={LOADING_LABEL}>
          <YearSVG className={styles.yearSVG} />
        </React.Suspense>
      )}
      <hr color="red" />
    </div>
  );
};

export default YearStat;
