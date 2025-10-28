// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class GetLabelResponseBodyData extends $dara.Model {
  labels?: string;
  static names(): { [key: string]: string } {
    return {
      labels: 'Labels',
    };
  }

  static types(): { [key: string]: any } {
    return {
      labels: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

